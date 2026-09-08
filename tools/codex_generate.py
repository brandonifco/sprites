#!/usr/bin/env python3
"""
Codex image generation agent.

Calls the OpenAI Images API to generate sprite images from text prompts.
Uses gpt-image-1 (the model Luna delegates to for image generation).

Requires OPENAI_API_KEY environment variable.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

import requests


def generate_image(
    prompt: str,
    output_path: Path,
    *,
    api_base: str = "https://api.openai.com/v1",
    model: str = "gpt-image-1",
    quality: str = "medium",
    size: str = "1024x1024",
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> tuple[bool, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return False, "OPENAI_API_KEY environment variable not set"

    url = f"{api_base}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "response_format": "b64_json",
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                url, headers=headers, json=payload, timeout=120
            )
            if resp.status_code == 429:
                wait = retry_delay * attempt
                if attempt < max_retries:
                    time.sleep(wait)
                    continue
                return False, f"rate limited after {max_retries} attempts"

            if resp.status_code != 200:
                error_msg = resp.text[:200]
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return False, f"API error {resp.status_code}: {error_msg}"

            data = resp.json()
            image_b64 = data["data"][0]["b64_json"]
            image_bytes = base64.b64decode(image_b64)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_bytes)

            revised = data["data"][0].get("revised_prompt", "")
            return True, revised if revised else "generated"

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            return False, "request timed out"
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            return False, f"connection error: {e}"
        except (KeyError, json.JSONDecodeError) as e:
            return False, f"unexpected response format: {e}"

    return False, "exhausted retries"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a sprite image from a text prompt via OpenAI API."
    )
    parser.add_argument("prompt_file", type=Path, help="Text file containing the prompt")
    parser.add_argument("output", type=Path, help="Output PNG path")
    parser.add_argument("--model", default="gpt-image-1")
    parser.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()

    prompt = args.prompt_file.read_text(encoding="utf-8").strip()
    if not prompt:
        print("ERROR: empty prompt file")
        return 1

    print(f"Generating image: {args.output.name} ({args.model}, {args.quality})")
    ok, msg = generate_image(
        prompt,
        args.output,
        model=args.model,
        quality=args.quality,
        size=args.size,
        max_retries=args.max_retries,
    )

    if ok:
        print(f"  saved to {args.output}")
        return 0
    else:
        print(f"  FAILED: {msg}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
