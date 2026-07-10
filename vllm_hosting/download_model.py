"""
Download both Findable models from HuggingFace to local disk.
Run once before starting the server.

Usage:
    python download_model.py
    python download_model.py --dir /workspace/models   # custom location
    python download_model.py --token hf_xxx            # if models are gated
    python download_model.py --heavy-only              # skip 2B-it
    python download_model.py --light-only              # skip 9B-it
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

MODELS = {
    "light": {
        "repo":  "google/gemma-2-2b-it",
        "label": "Gemma 2 2B IT  (light / crawlability sub-agent)",
        "size":  "~5 GB",
    },
    "heavy": {
        "repo":  "google/gemma-2-9b-it",
        "label": "Gemma 2 9B IT  (heavy / judgment + content agents)",
        "size":  "~18-22 GB",
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_huggingface_hub():
    try:
        import huggingface_hub
        return huggingface_hub
    except ImportError:
        print("huggingface_hub not found — installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "huggingface_hub[cli]"], check=True)
        import huggingface_hub
        return huggingface_hub


def download_model(repo: str, label: str, size: str, dest_dir: Path,
                   token: str | None) -> Path:
    hf = check_huggingface_hub()

    local_dir = dest_dir / repo.replace("/", "--")
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Repo  : {repo}")
    print(f"  Size  : {size} on disk")
    print(f"  Dest  : {local_dir}")
    print(f"{'='*60}")

    if (local_dir / "config.json").exists():
        print("  Already downloaded — skipping.")
        return local_dir

    local_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    try:
        hf.snapshot_download(
            repo_id=repo,
            local_dir=str(local_dir),
            token=token or None,
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*",
                              "rust_model*", "model.safetensors.index.json.lock"],
        )
    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        if "401" in str(exc) or "403" in str(exc):
            print("  The model may be gated. Check the HuggingFace model page")
            print("  and pass --token hf_... if you see a licence gate.")
        sys.exit(1)

    elapsed = time.time() - t0
    size_gb = sum(f.stat().st_size for f in local_dir.rglob("*") if f.is_file()) / 1e9
    print(f"\n  Done in {elapsed/60:.1f} min  ({size_gb:.1f} GB on disk)")
    return local_dir


def verify_model(local_dir: Path) -> bool:
    required = ["config.json", "tokenizer_config.json"]
    missing = [f for f in required if not (local_dir / f).exists()]
    if missing:
        print(f"  WARNING: missing files after download: {missing}")
        return False

    weight_files = list(local_dir.glob("*.safetensors")) + list(local_dir.glob("*.bin"))
    print(f"  Verified: {len(weight_files)} weight shard(s) present")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Download Findable models to local disk")
    parser.add_argument("--dir",        default="/workspace/models",
                        help="Root directory for downloaded models (default: /workspace/models)")
    parser.add_argument("--token",      default=os.environ.get("HF_TOKEN", ""),
                        help="HuggingFace read token (only needed for gated models)")
    parser.add_argument("--heavy-only", action="store_true", help="Download heavy model only")
    parser.add_argument("--light-only", action="store_true", help="Download light model only")
    args = parser.parse_args()

    dest_dir = Path(args.dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    token = args.token or None
    if token:
        print(f"Using HF token: {token[:8]}...")
    else:
        print("No HF token set - assuming model access has already been accepted if gated")

    to_download = []
    if not args.heavy_only:
        to_download.append("light")
    if not args.light_only:
        to_download.append("heavy")

    paths: dict[str, Path] = {}
    total_start = time.time()

    for key in to_download:
        m = MODELS[key]
        local_dir = download_model(
            repo=m["repo"], label=m["label"], size=m["size"],
            dest_dir=dest_dir, token=token,
        )
        verify_model(local_dir)
        paths[key] = local_dir

    print(f"\n{'='*60}")
    print("All downloads complete.")
    print(f"Total time: {(time.time()-total_start)/60:.1f} min")
    print()
    print("Paths to use in start_service.sh:")
    for key, path in paths.items():
        var = "LIGHT_MODEL_PATH" if key == "light" else "HEAVY_MODEL_PATH"
        print(f"  {var}={path}")
    print()
    print("Next step:  bash start_service.sh")


if __name__ == "__main__":
    main()
