# GodotForge GDScript Fine-Tuning Pipeline

Fine-tune a code LLM on GDScript instruction-response pairs so that GodotForge can
run a local, Godot-specialised coding assistant via Ollama.

The approach is inspired by the **godot-dodo** methodology: scrape high-quality
GDScript from public repositories, synthesise instruction-code pairs with a
teacher LLM, filter for quality, fine-tune with LoRA + 4-bit quantisation, and
export to GGUF for local inference.

## Pipeline Overview

```
1. Scrape       ->  Collect .gd files from GitHub (Godot 4.x projects)
2. Instruct     ->  Use a teacher LLM to generate (instruction, code) pairs
3. Filter       ->  Remove low-quality / too-short / syntactically broken pairs
4. Train        ->  LoRA fine-tune deepseek-coder-6.7b with Unsloth + SFTTrainer
5. Export       ->  Convert to GGUF (q5_k_m quantisation)
6. Register     ->  Create an Ollama model via Modelfile
```

## Directory Layout

```
finetune/
  README.md            # This file
  train_config.yaml    # Hyperparameters and paths
  train.py             # Training script (Unsloth + HuggingFace TRL)
  prepare_data.py      # Data scraping and instruction generation
  Modelfile            # Ollama Modelfile for the exported model
```

## Hardware Requirements

| Stage       | GPU VRAM | RAM   | Disk   | Notes                              |
|-------------|----------|-------|--------|------------------------------------|
| Scraping    | -        | 4 GB  | 10 GB  | Network-bound; GitHub API token    |
| Instruction | -        | 4 GB  | -      | Uses external LLM API              |
| Training    | >= 16 GB | 32 GB | 40 GB  | Tested on A100-40G / RTX 4090      |
| Export GGUF | >= 8 GB  | 32 GB | 20 GB  | llama.cpp quantisation             |

A single NVIDIA RTX 4090 (24 GB) is sufficient for the full training loop when
using 4-bit QLoRA.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements-finetune.txt
# Or manually:
pip install unsloth transformers trl datasets peft accelerate \
            bitsandbytes sentencepiece protobuf pyyaml requests
```

### 2. Scrape GDScript from GitHub

```bash
python prepare_data.py scrape \
    --output data/raw_gdscript.jsonl \
    --max-repos 500 \
    --github-token "$GITHUB_TOKEN"
```

### 3. Generate instruction-code pairs

```bash
python prepare_data.py instruct \
    --input data/raw_gdscript.jsonl \
    --output data/instruct_pairs.jsonl \
    --provider anthropic \
    --model claude-sonnet-4-20250514
```

### 4. Filter dataset

```bash
python prepare_data.py filter \
    --input data/instruct_pairs.jsonl \
    --output data/train_data.jsonl \
    --min-code-length 40 \
    --max-code-length 8000
```

### 5. Train

```bash
python train.py --config train_config.yaml
```

### 6. Export to GGUF

The training script exports GGUF automatically. You can also do it manually:

```bash
python train.py --config train_config.yaml --export-only
```

### 7. Register with Ollama

```bash
# Edit Modelfile to point to the real GGUF path, then:
ollama create godotforge-coder -f Modelfile
ollama run godotforge-coder "Write a CharacterBody2D movement script"
```

## Configuration

All training hyperparameters live in `train_config.yaml`. Key knobs:

- `lora.r` / `lora.alpha` -- LoRA rank and scaling
- `training.learning_rate` -- start with 2e-5; lower if loss spikes
- `training.num_epochs` -- 3 is a good default; 5 for small datasets
- `training.max_seq_length` -- 4096 tokens covers most GDScript files

## Dataset Format

Each line in the training JSONL is:

```json
{
  "instruction": "Write a GDScript function that ...",
  "input": "",
  "output": "extends Node\n\nfunc _ready():\n    ..."
}
```

The `input` field is optional context (e.g., an existing class skeleton).

## License

Training data is collected only from repositories with permissive licences
(MIT, Apache-2.0, BSD, CC0). The fine-tuned model inherits the base model
licence (deepseek-coder: permissive for research and commercial use).
