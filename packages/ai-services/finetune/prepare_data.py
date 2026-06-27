#!/usr/bin/env python3
"""
GodotForge GDScript Data Preparation
======================================

Three-stage pipeline:

  1. **scrape**    -- Collect .gd files from public GitHub repos (Godot 4.x).
  2. **instruct**  -- Generate (instruction, code) pairs with a teacher LLM.
  3. **filter**    -- Remove low-quality entries (too short, too long, broken syntax).

Usage:
    python prepare_data.py scrape   --output data/raw_gdscript.jsonl [OPTIONS]
    python prepare_data.py instruct --input data/raw_gdscript.jsonl --output data/instruct_pairs.jsonl [OPTIONS]
    python prepare_data.py filter   --input data/instruct_pairs.jsonl --output data/train_data.jsonl [OPTIONS]
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("godotforge-data")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
GITHUB_SEARCH_REPOS = f"{GITHUB_API}/search/repositories"
GITHUB_SEARCH_CODE = f"{GITHUB_API}/search/code"

# Licences we consider permissive enough for training data
PERMISSIVE_LICENCES = {
    "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause",
    "isc", "unlicense", "cc0-1.0", "0bsd", "wtfpl",
}

# Teacher prompt for generating instruction-code pairs
INSTRUCTION_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert Godot 4.x game developer and technical writer.
    Given a GDScript code snippet, generate a concise natural-language
    instruction that a developer might give to produce this code.

    Rules:
    - The instruction should be a clear, standalone request.
    - Start with an action verb (Write, Create, Implement, Add, ...).
    - Do NOT repeat the code in the instruction.
    - Keep the instruction to 1-3 sentences.
    - If the code is trivial (< 3 meaningful lines), output exactly: SKIP

    Respond with ONLY the instruction text (or SKIP). No markdown, no quotes.
""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gh_headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _rate_limit_wait(response: requests.Response) -> None:
    """Sleep until GitHub rate limit resets if we're close to exhausting it."""
    remaining = int(response.headers.get("X-RateLimit-Remaining", 999))
    if remaining < 3:
        reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
        wait = max(reset_ts - int(time.time()), 1) + 2
        logger.warning("Rate limit nearly exhausted, sleeping %ds ...", wait)
        time.sleep(wait)


# ============================================================================
# Stage 1: Scrape
# ============================================================================

def search_godot_repos(
    token: str | None,
    max_repos: int = 500,
    min_stars: int = 5,
) -> list[dict]:
    """
    Search GitHub for Godot 4.x repos with permissive licences.
    Returns list of {full_name, html_url, license, stargazers_count}.
    """
    repos: list[dict] = []
    page = 1
    per_page = 100
    headers = _gh_headers(token)

    while len(repos) < max_repos:
        query = f"godot language:GDScript stars:>={min_stars}"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }

        resp = requests.get(GITHUB_SEARCH_REPOS, headers=headers, params=params)
        _rate_limit_wait(resp)

        if resp.status_code != 200:
            logger.error("Repo search failed (%d): %s", resp.status_code, resp.text[:300])
            break

        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        for repo in items:
            licence_info = repo.get("license") or {}
            licence_key = (licence_info.get("spdx_id") or "").lower()
            if licence_key not in PERMISSIVE_LICENCES:
                continue
            repos.append({
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "license": licence_key,
                "stargazers_count": repo["stargazers_count"],
            })
            if len(repos) >= max_repos:
                break

        page += 1
        # GitHub search API caps at 1000 results
        if page * per_page > 1000:
            break
        time.sleep(1)  # Be polite

    logger.info("Found %d permissive-licence Godot repos", len(repos))
    return repos


def fetch_gd_files_from_repo(
    full_name: str,
    token: str | None,
    max_files: int = 50,
) -> list[dict]:
    """
    Retrieve .gd files from a repo using the GitHub code search API.
    Returns list of {path, content, repo}.
    """
    headers = _gh_headers(token)
    files: list[dict] = []

    # Use the Trees API instead of code search (more reliable for bulk)
    # First get the default branch SHA
    repo_resp = requests.get(f"{GITHUB_API}/repos/{full_name}", headers=headers)
    _rate_limit_wait(repo_resp)
    if repo_resp.status_code != 200:
        return files

    default_branch = repo_resp.json().get("default_branch", "main")

    # Get the full tree recursively
    tree_url = f"{GITHUB_API}/repos/{full_name}/git/trees/{default_branch}?recursive=1"
    tree_resp = requests.get(tree_url, headers=headers)
    _rate_limit_wait(tree_resp)
    if tree_resp.status_code != 200:
        return files

    tree_data = tree_resp.json()
    gd_entries = [
        entry for entry in tree_data.get("tree", [])
        if entry.get("path", "").endswith(".gd")
        and entry.get("type") == "blob"
        and entry.get("size", 0) < 50_000  # Skip very large files
    ]

    # Sort by size descending so we get the meatier scripts first
    gd_entries.sort(key=lambda e: e.get("size", 0), reverse=True)

    for entry in gd_entries[:max_files]:
        blob_url = entry["url"]
        blob_resp = requests.get(blob_url, headers=headers)
        _rate_limit_wait(blob_resp)
        if blob_resp.status_code != 200:
            continue

        blob = blob_resp.json()
        content_b64 = blob.get("content", "")
        try:
            content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        except Exception:
            continue

        # Quick filter: must look like valid GDScript
        if not (content.strip().startswith("extends") or
                content.strip().startswith("class_name") or
                "func " in content):
            continue

        files.append({
            "path": entry["path"],
            "content": content,
            "repo": full_name,
        })

        time.sleep(0.2)

    return files


def cmd_scrape(args: argparse.Namespace) -> None:
    """Scrape GDScript files from GitHub and write to JSONL."""
    token = args.github_token or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.warning(
            "No GitHub token provided. Rate limits will be very low (60 req/hr)."
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    repos = search_godot_repos(
        token=token,
        max_repos=args.max_repos,
        min_stars=args.min_stars,
    )

    total_files = 0

    with open(output_path, "w", encoding="utf-8") as fh:
        for i, repo in enumerate(repos):
            logger.info(
                "[%d/%d] Scraping %s (stars: %d) ...",
                i + 1, len(repos), repo["full_name"], repo["stargazers_count"],
            )

            gd_files = fetch_gd_files_from_repo(
                full_name=repo["full_name"],
                token=token,
                max_files=args.max_files_per_repo,
            )

            for gf in gd_files:
                record = {
                    "repo": gf["repo"],
                    "path": gf["path"],
                    "license": repo["license"],
                    "code": gf["content"],
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_files += 1

            # Pace ourselves
            time.sleep(1)

    logger.info(
        "Scraping complete: %d files from %d repos -> %s",
        total_files, len(repos), output_path,
    )


# ============================================================================
# Stage 2: Instruction Generation
# ============================================================================

def generate_instruction_anthropic(code: str, model: str, api_key: str) -> str | None:
    """Call Anthropic Messages API to generate an instruction for the code."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=256,
        system=INSTRUCTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"```gdscript\n{code}\n```"}],
    )
    text = message.content[0].text.strip()
    if text.upper() == "SKIP":
        return None
    return text


def generate_instruction_openai(code: str, model: str, api_key: str) -> str | None:
    """Call OpenAI Chat Completions API to generate an instruction."""
    import openai

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=256,
        messages=[
            {"role": "system", "content": INSTRUCTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"```gdscript\n{code}\n```"},
        ],
    )
    text = response.choices[0].message.content.strip()
    if text.upper() == "SKIP":
        return None
    return text


def generate_instruction_ollama(code: str, model: str, base_url: str) -> str | None:
    """Call a local Ollama instance to generate an instruction."""
    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": INSTRUCTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"```gdscript\n{code}\n```"},
        ],
    }
    resp = requests.post(url, json=payload, timeout=120)
    if resp.status_code != 200:
        return None
    text = resp.json().get("message", {}).get("content", "").strip()
    if text.upper() == "SKIP":
        return None
    return text


def _get_instruction_generator(args: argparse.Namespace):
    """Return a callable (code -> instruction_or_none) based on provider."""
    provider = args.provider.lower()

    if provider == "anthropic":
        api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key required (--api-key or ANTHROPIC_API_KEY)")
        model = args.model or "claude-sonnet-4-20250514"
        return lambda code: generate_instruction_anthropic(code, model, api_key)

    elif provider == "openai":
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required (--api-key or OPENAI_API_KEY)")
        model = args.model or "gpt-4o-mini"
        return lambda code: generate_instruction_openai(code, model, api_key)

    elif provider == "ollama":
        model = args.model or "llama3"
        base_url = args.ollama_url or "http://localhost:11434"
        return lambda code: generate_instruction_ollama(code, model, base_url)

    else:
        raise ValueError(f"Unknown provider: {provider}")


def cmd_instruct(args: argparse.Namespace) -> None:
    """Generate instruction-code pairs from raw scraped GDScript."""
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_fn = _get_instruction_generator(args)

    # Load existing output to support resume
    existing_keys: set[str] = set()
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    existing_keys.add(f"{rec.get('repo')}::{rec.get('path')}")
        logger.info("Resuming -- %d existing pairs found", len(existing_keys))

    total = 0
    skipped = 0
    errors = 0

    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "a", encoding="utf-8") as fout:

        for line_no, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = f"{record['repo']}::{record['path']}"

            if key in existing_keys:
                continue

            code = record["code"]

            try:
                instruction = generate_fn(code)
            except Exception as exc:
                logger.warning("Error generating instruction for %s: %s", key, exc)
                errors += 1
                time.sleep(2)
                continue

            if instruction is None:
                skipped += 1
                continue

            pair = {
                "instruction": instruction,
                "input": "",
                "output": code,
                "repo": record["repo"],
                "path": record["path"],
                "license": record.get("license", ""),
            }
            fout.write(json.dumps(pair, ensure_ascii=False) + "\n")
            total += 1

            if total % 50 == 0:
                logger.info("Generated %d pairs (%d skipped, %d errors) ...", total, skipped, errors)

            # Rate limiting
            time.sleep(args.delay)

    logger.info(
        "Instruction generation complete: %d pairs, %d skipped, %d errors -> %s",
        total, skipped, errors, output_path,
    )


# ============================================================================
# Stage 3: Filter
# ============================================================================

def validate_gdscript_syntax(code: str) -> bool:
    """
    Basic GDScript syntax validation.

    Checks for:
    - Balanced parentheses, brackets, braces
    - Valid top-level keywords
    - No obviously broken indentation patterns
    """
    # Check balanced delimiters
    stack: list[str] = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    in_string = False
    string_char = ""

    for ch in code:
        if in_string:
            if ch == string_char:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            continue
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack[-1] != ch:
                return False
            stack.pop()

    if stack:
        return False

    # Must have at least one function or extends declaration
    lines = code.strip().split("\n")
    has_structure = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith(("#", "//")) or not stripped:
            continue
        if any(stripped.startswith(kw) for kw in (
            "extends", "class_name", "func ", "static func ",
            "signal ", "var ", "const ", "enum ", "class ",
            "@export", "@onready", "@tool",
        )):
            has_structure = True
            break

    return has_structure


def cmd_filter(args: argparse.Namespace) -> None:
    """Filter instruction-code pairs by quality heuristics."""
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    min_len = args.min_code_length
    max_len = args.max_code_length
    min_instruction_len = args.min_instruction_length

    total = 0
    kept = 0
    reasons: dict[str, int] = {
        "too_short": 0,
        "too_long": 0,
        "instruction_too_short": 0,
        "syntax_invalid": 0,
        "duplicate": 0,
    }

    seen_instructions: set[str] = set()

    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for line in fin:
            line = line.strip()
            if not line:
                continue
            total += 1
            record = json.loads(line)

            code = record.get("output", "")
            instruction = record.get("instruction", "")

            # Length checks
            if len(code) < min_len:
                reasons["too_short"] += 1
                continue
            if len(code) > max_len:
                reasons["too_long"] += 1
                continue
            if len(instruction) < min_instruction_len:
                reasons["instruction_too_short"] += 1
                continue

            # De-duplication by instruction text (normalised)
            norm_instr = re.sub(r"\s+", " ", instruction.lower().strip())
            if norm_instr in seen_instructions:
                reasons["duplicate"] += 1
                continue
            seen_instructions.add(norm_instr)

            # Syntax validation
            if not validate_gdscript_syntax(code):
                reasons["syntax_invalid"] += 1
                continue

            # Passed all filters -- write the clean training record
            clean_record = {
                "instruction": instruction,
                "input": record.get("input", ""),
                "output": code,
            }
            fout.write(json.dumps(clean_record, ensure_ascii=False) + "\n")
            kept += 1

    logger.info(
        "Filtering complete: %d/%d kept (%.1f%%)",
        kept, total, 100 * kept / max(total, 1),
    )
    for reason, count in sorted(reasons.items()):
        if count > 0:
            logger.info("  Rejected %-25s %d", reason, count)

    logger.info("Output: %s", output_path)


# ============================================================================
# CLI entry point
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GodotForge GDScript data preparation pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- scrape ---------------------------------------------------------------
    sp_scrape = subparsers.add_parser("scrape", help="Scrape .gd files from GitHub")
    sp_scrape.add_argument(
        "--output", type=str, required=True,
        help="Output JSONL file path",
    )
    sp_scrape.add_argument(
        "--max-repos", type=int, default=500,
        help="Maximum number of repos to scrape (default: 500)",
    )
    sp_scrape.add_argument(
        "--max-files-per-repo", type=int, default=50,
        help="Maximum .gd files per repo (default: 50)",
    )
    sp_scrape.add_argument(
        "--min-stars", type=int, default=5,
        help="Minimum star count for repos (default: 5)",
    )
    sp_scrape.add_argument(
        "--github-token", type=str, default=None,
        help="GitHub personal access token (or set GITHUB_TOKEN env var)",
    )

    # -- instruct -------------------------------------------------------------
    sp_instruct = subparsers.add_parser(
        "instruct", help="Generate instruction-code pairs via LLM"
    )
    sp_instruct.add_argument(
        "--input", type=str, required=True,
        help="Input JSONL from scrape stage",
    )
    sp_instruct.add_argument(
        "--output", type=str, required=True,
        help="Output JSONL with instruction-code pairs",
    )
    sp_instruct.add_argument(
        "--provider", type=str, default="anthropic",
        choices=["anthropic", "openai", "ollama"],
        help="LLM provider for instruction generation (default: anthropic)",
    )
    sp_instruct.add_argument(
        "--model", type=str, default=None,
        help="Model name (provider-specific; defaults per provider)",
    )
    sp_instruct.add_argument(
        "--api-key", type=str, default=None,
        help="API key (or set ANTHROPIC_API_KEY / OPENAI_API_KEY env var)",
    )
    sp_instruct.add_argument(
        "--ollama-url", type=str, default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    sp_instruct.add_argument(
        "--delay", type=float, default=0.5,
        help="Delay between API calls in seconds (default: 0.5)",
    )

    # -- filter ---------------------------------------------------------------
    sp_filter = subparsers.add_parser(
        "filter", help="Filter and clean instruction-code pairs"
    )
    sp_filter.add_argument(
        "--input", type=str, required=True,
        help="Input JSONL from instruct stage",
    )
    sp_filter.add_argument(
        "--output", type=str, required=True,
        help="Output JSONL with filtered pairs",
    )
    sp_filter.add_argument(
        "--min-code-length", type=int, default=40,
        help="Minimum code length in characters (default: 40)",
    )
    sp_filter.add_argument(
        "--max-code-length", type=int, default=8000,
        help="Maximum code length in characters (default: 8000)",
    )
    sp_filter.add_argument(
        "--min-instruction-length", type=int, default=10,
        help="Minimum instruction length in characters (default: 10)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "instruct":
        cmd_instruct(args)
    elif args.command == "filter":
        cmd_filter(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
