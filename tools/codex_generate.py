#!/usr/bin/env python3
"""
Codex image generation agent.

Invokes the OpenAI Codex CLI (npx @openai/codex exec) to generate sprite
images. Uses the user's ChatGPT Pro subscription — no API key needed.

Codex uses its built-in image_gen tool with whatever model is configured
in ~/.codex/config.toml (default: gpt-5.6-luna, medium effort).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def generate_image(
    prompt: str,
    output_path: Path,
    timeout: int = 180,
) -> tuple[bool, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    codex_prompt = (
        f"Generate a sprite image matching this description and save it as "
        f"{output_path}. Do NOT resize the image — save it at whatever "
        f"resolution is generated. Here is the full prompt:\n\n{prompt}"
    )

    try:
        result = subprocess.run(
            [
                "npx", "@openai/codex", "exec",
                "-s", "workspace-write",
                "--skip-git-repo-check",
                "--ephemeral",
                "-C", str(output_path.parent.resolve()),
                codex_prompt,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            input="",
        )
    except subprocess.TimeoutExpired:
        return False, f"codex timed out after {timeout}s"
    except FileNotFoundError:
        return False, "npx or @openai/codex not found — install with: npm install -g @openai/codex"

    if output_path.exists() and output_path.stat().st_size > 0:
        return True, "generated"

    stderr = result.stderr[-500:] if result.stderr else ""
    stdout = result.stdout[-500:] if result.stdout else ""
    return False, f"codex exited {result.returncode}, no image produced. {stderr or stdout}"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a sprite image via Codex CLI."
    )
    parser.add_argument("prompt_file", type=Path, help="Text file containing the prompt")
    parser.add_argument("output", type=Path, help="Output PNG path")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    prompt = args.prompt_file.read_text(encoding="utf-8").strip()
    if not prompt:
        print("ERROR: empty prompt file")
        return 1

    print(f"Codex generating: {args.output.name}")
    ok, msg = generate_image(prompt, args.output, timeout=args.timeout)

    if ok:
        print(f"  saved to {args.output}")
        return 0
    else:
        print(f"  FAILED: {msg}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
