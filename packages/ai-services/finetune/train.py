#!/usr/bin/env python3
"""
GodotForge GDScript Fine-Tuning Script
=======================================

Fine-tunes a code LLM on GDScript instruction-response pairs using Unsloth
(4-bit QLoRA) and HuggingFace TRL's SFTTrainer.

Usage:
    python train.py --config train_config.yaml
    python train.py --config train_config.yaml --export-only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("godotforge-train")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    """Load YAML configuration and return as dict."""
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    logger.info("Loaded config from %s", path)
    return cfg


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def load_dataset_from_jsonl(file_path: str, eval_split: float = 0.05):
    """
    Load a JSONL file with instruction / input / output fields and return
    a HuggingFace DatasetDict with 'train' (and optionally 'test') splits.
    """
    from datasets import Dataset, DatasetDict

    records: list[dict] = []
    with open(file_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    logger.info("Loaded %d records from %s", len(records), file_path)

    ds = Dataset.from_list(records)

    if eval_split > 0:
        split = ds.train_test_split(test_size=eval_split, seed=42)
        return DatasetDict({"train": split["train"], "test": split["test"]})
    return DatasetDict({"train": ds})


def format_dataset(dataset_dict, prompt_template: str, max_seq_length: int):
    """
    Apply the prompt template to every example and tokenise-friendly text
    column named 'text'.
    """

    def _apply_template(example: dict) -> dict:
        text = prompt_template.format(
            instruction=example.get("instruction", ""),
            input=example.get("input", ""),
            output=example.get("output", ""),
        )
        # Truncate at character level as a rough guard; the tokeniser will
        # handle the real truncation.
        return {"text": text[:max_seq_length * 6]}

    for split in dataset_dict:
        dataset_dict[split] = dataset_dict[split].map(
            _apply_template, remove_columns=dataset_dict[split].column_names
        )

    logger.info(
        "Formatted dataset -- train: %d, eval: %d",
        len(dataset_dict["train"]),
        len(dataset_dict.get("test", [])),
    )
    return dataset_dict


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model_and_tokenizer(cfg: dict):
    """
    Load the base model in 4-bit via Unsloth's FastLanguageModel and apply
    LoRA adapters.
    """
    from unsloth import FastLanguageModel

    model_cfg = cfg["model"]
    lora_cfg = cfg["lora"]
    ds_cfg = cfg["dataset"]

    logger.info("Loading base model: %s", model_cfg["name"])

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_cfg["name"],
        max_seq_length=ds_cfg["max_seq_length"],
        dtype=None,  # auto-detect
        load_in_4bit=model_cfg.get("load_in_4bit", True),
        trust_remote_code=model_cfg.get("trust_remote_code", True),
    )

    logger.info(
        "Applying LoRA -- r=%d, alpha=%d, dropout=%.3f, targets=%s",
        lora_cfg["r"],
        lora_cfg["alpha"],
        lora_cfg["dropout"],
        lora_cfg["target_modules"],
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        target_modules=lora_cfg["target_modules"],
        bias=lora_cfg.get("bias", "none"),
        use_gradient_checkpointing="unsloth",  # long-context optimisation
        random_state=cfg["training"].get("seed", 42),
    )

    return model, tokenizer


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def build_trainer(model, tokenizer, dataset_dict, cfg: dict):
    """Construct an SFTTrainer from the configuration."""
    from trl import SFTTrainer
    from transformers import TrainingArguments

    tcfg = cfg["training"]
    ds_cfg = cfg["dataset"]

    training_args = TrainingArguments(
        output_dir=tcfg["output_dir"],
        num_train_epochs=tcfg["num_epochs"],
        per_device_train_batch_size=tcfg["per_device_train_batch_size"],
        gradient_accumulation_steps=tcfg["gradient_accumulation_steps"],
        learning_rate=tcfg["learning_rate"],
        weight_decay=tcfg.get("weight_decay", 0.01),
        warmup_ratio=tcfg.get("warmup_ratio", 0.03),
        lr_scheduler_type=tcfg.get("lr_scheduler_type", "cosine"),
        fp16=tcfg.get("fp16", True),
        bf16=tcfg.get("bf16", False),
        logging_steps=tcfg.get("logging_steps", 10),
        save_steps=tcfg.get("save_steps", 200),
        save_total_limit=tcfg.get("save_total_limit", 3),
        seed=tcfg.get("seed", 42),
        optim=tcfg.get("optim", "adamw_8bit"),
        gradient_checkpointing=tcfg.get("gradient_checkpointing", True),
        max_grad_norm=tcfg.get("max_grad_norm", 1.0),
        report_to=tcfg.get("report_to", "none"),
        # Evaluation
        eval_strategy="steps" if "test" in dataset_dict else "no",
        eval_steps=tcfg.get("save_steps", 200) if "test" in dataset_dict else None,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset_dict["train"],
        eval_dataset=dataset_dict.get("test"),
        args=training_args,
        dataset_text_field="text",
        max_seq_length=ds_cfg["max_seq_length"],
        packing=True,  # Unsloth efficient packing
    )

    return trainer


def run_training(cfg: dict) -> str:
    """Full training pipeline. Returns path to output directory."""
    # Dataset ------------------------------------------------------------------
    ds_cfg = cfg["dataset"]
    train_file = ds_cfg["train_file"]
    eval_file = ds_cfg.get("eval_file", "")

    if eval_file:
        from datasets import DatasetDict

        train_ds = load_dataset_from_jsonl(train_file, eval_split=0)
        eval_ds = load_dataset_from_jsonl(eval_file, eval_split=0)
        dataset_dict = DatasetDict(
            {"train": train_ds["train"], "test": eval_ds["train"]}
        )
    else:
        dataset_dict = load_dataset_from_jsonl(
            train_file, eval_split=ds_cfg.get("eval_split", 0.05)
        )

    dataset_dict = format_dataset(
        dataset_dict,
        prompt_template=ds_cfg["prompt_template"],
        max_seq_length=ds_cfg["max_seq_length"],
    )

    # Model --------------------------------------------------------------------
    model, tokenizer = load_model_and_tokenizer(cfg)

    # Trainer ------------------------------------------------------------------
    trainer = build_trainer(model, tokenizer, dataset_dict, cfg)

    logger.info("Starting training ...")
    train_result = trainer.train()

    metrics = train_result.metrics
    logger.info("Training complete -- loss=%.4f", metrics.get("train_loss", -1))

    # Save adapter + tokenizer -------------------------------------------------
    output_dir = cfg["training"]["output_dir"]
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info("Saved adapter to %s", output_dir)

    return output_dir


# ---------------------------------------------------------------------------
# GGUF export
# ---------------------------------------------------------------------------

def export_gguf(cfg: dict, adapter_dir: str | None = None):
    """
    Merge LoRA adapter back into the base model and export as a GGUF file
    using Unsloth's built-in converter.
    """
    from unsloth import FastLanguageModel

    export_cfg = cfg.get("export", {})
    if not export_cfg.get("enabled", True):
        logger.info("GGUF export disabled in config -- skipping.")
        return

    if adapter_dir is None:
        adapter_dir = cfg["training"]["output_dir"]

    ds_cfg = cfg["dataset"]
    quant = export_cfg.get("quantisation", "q5_k_m")
    output_dir = export_cfg.get("output_dir", "outputs/gguf")
    output_name = export_cfg.get("output_name", "godotforge-coder")

    os.makedirs(output_dir, exist_ok=True)

    logger.info("Loading adapter from %s for GGUF export ...", adapter_dir)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter_dir,
        max_seq_length=ds_cfg["max_seq_length"],
        dtype=None,
        load_in_4bit=False,  # Need full precision for export
    )

    logger.info("Exporting to GGUF (%s) -> %s", quant, output_dir)

    model.save_pretrained_gguf(
        output_dir,
        tokenizer,
        quantization_method=quant,
    )

    # Rename to a friendlier filename
    expected_name = f"{output_name}.Q5_K_M.gguf"
    final_path = os.path.join(output_dir, expected_name)
    logger.info("GGUF export complete: %s", final_path)

    return final_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GodotForge GDScript fine-tuning with Unsloth + QLoRA",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="train_config.yaml",
        help="Path to YAML configuration file (default: train_config.yaml)",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Skip training; only run GGUF export from an existing adapter.",
    )
    parser.add_argument(
        "--adapter-dir",
        type=str,
        default=None,
        help="Path to a saved LoRA adapter (used with --export-only).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    if args.export_only:
        adapter_dir = args.adapter_dir or cfg["training"]["output_dir"]
        export_gguf(cfg, adapter_dir=adapter_dir)
    else:
        output_dir = run_training(cfg)
        export_gguf(cfg, adapter_dir=output_dir)

    logger.info("All done.")


if __name__ == "__main__":
    main()
