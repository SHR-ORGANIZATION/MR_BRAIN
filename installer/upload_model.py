#!/usr/bin/env python3
"""
AMAZON AI - Upload ML Model to GitHub Releases
─────────────────────────────────────────────────────────────────────────────
The ML model files are too large for regular git.
This script zips them and uploads to a GitHub Release so CI can download them.

Prerequisites:
    pip install ghapi
    gh auth login   (GitHub CLI must be authenticated)

Usage:
    python installer/upload_model.py              # Upload to 'latest' release
    python installer/upload_model.py --create     # Create release if it doesn't exist
    python installer/upload_model.py --tag v1.0.0 # Upload to specific tag
"""
import sys
import os
import zipfile
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"

# Files needed at runtime (excludes training checkpoints)
MODEL_FILES = [
    "ml/nlu_model/config.json",
    "ml/nlu_model/amazon_config.json",
    "ml/nlu_model/nova_config.json",
    "ml/nlu_model/model.safetensors",
    "ml/nlu_model/vocab.txt",
    "ml/nlu_model/tokenizer_config.json",
    "ml/nlu_model/special_tokens_map.json",
    "ml/semantic_index/metadata.json",
    "ml/semantic_index/vectors.faiss",
    "ml/label_map.json",
]

ASSET_NAME = "ml_model_essentials.zip"


def check_files():
    """Check which model files exist."""
    found = []
    missing = []
    for f in MODEL_FILES:
        path = ROOT / f
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            found.append((f, size_mb))
        else:
            missing.append(f)
    return found, missing


def create_zip(output_path):
    """Create a zip of all model files."""
    print(f"\n📦 Creating {ASSET_NAME}...")
    total_size = 0

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel_path in MODEL_FILES:
            full_path = ROOT / rel_path
            if full_path.exists():
                size_mb = full_path.stat().st_size / (1024 * 1024)
                print(f"  + {rel_path} ({size_mb:.1f} MB)")
                zf.write(full_path, rel_path)
                total_size += full_path.stat().st_size

    zip_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n✓ Zip created: {output_path}")
    print(f"  Contents: {len(MODEL_FILES)} files")
    print(f"  Uncompressed: {total_size / (1024*1024):.1f} MB")
    print(f"  Compressed: {zip_size_mb:.1f} MB")
    return output_path


def upload_to_release(zip_path, tag="latest", create=False):
    """Upload zip to GitHub Release using gh CLI."""
    print(f"\n📤 Uploading to GitHub Release '{tag}'...")

    # Check gh CLI
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ GitHub CLI (gh) not found. Install from: https://cli.github.com/")
        print("  Then run: gh auth login")
        sys.exit(1)

    # Check auth
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if result.returncode != 0:
        print("✗ Not authenticated. Run: gh auth login")
        sys.exit(1)

    # Get repo info
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("✗ Not in a git repo or no remote configured")
        sys.exit(1)

    import json
    repo = json.loads(result.stdout)["nameWithOwner"]
    print(f"  Repository: {repo}")

    # Create release if needed (skip if already exists)
    if create:
        print(f"  Creating release '{tag}' (or using existing)...")
        result = subprocess.run([
            "gh", "release", "create", tag,
            "--title", f"AMAZON AI {tag}",
            "--notes", f"ML model files for AMAZON AI {tag}",
        ], capture_output=True, text=True)
        if result.returncode != 0 and "already exists" not in result.stderr:
            print(f"  ✗ Failed to create release: {result.stderr}")
            sys.exit(1)
        print(f"  ✓ Release '{tag}' ready")

    # Delete old asset if exists
    subprocess.run([
        "gh", "release", "delete-asset", tag, ASSET_NAME,
        "--yes",
    ], capture_output=True)

    # Upload
    subprocess.run([
        "gh", "release", "upload", tag,
        str(zip_path),
        "--clobber",
    ], check=True)

    print(f"\n✓ Uploaded successfully!")
    print(f"  Release: {tag}")
    print(f"  Asset: {ASSET_NAME}")
    print(f"  URL: https://github.com/{repo}/releases/tag/{tag}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload ML model files to GitHub Releases for CI access"
    )
    parser.add_argument("--tag", default="latest", help="Release tag (default: latest)")
    parser.add_argument("--create", action="store_true", help="Create release if not exists")
    parser.add_argument("--zip-only", action="store_true", help="Only create zip, don't upload")
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  AMAZON AI - ML Model Uploader")
    print("=" * 55)

    found, missing = check_files()

    print(f"\n  Found: {len(found)} files")
    print(f"  Missing: {len(missing)} files")

    if missing:
        print("\n  Missing files:")
        for f in missing:
            print(f"    ✗ {f}")
        if not found:
            print("\n  No model files found! Train the model first:")
            print("    python ml/train_nlu.py")
            sys.exit(1)

    if not found:
        print("\n✗ No model files found. Train the model first:")
        print("  python ml/train_nlu.py")
        sys.exit(1)

    # Create zip
    zip_path = ROOT / "dist" / ASSET_NAME
    zip_path.parent.mkdir(exist_ok=True)
    create_zip(zip_path)

    if args.zip_only:
        print(f"\n✓ Zip saved to: {zip_path}")
        return

    # Upload
    upload_to_release(zip_path, tag=args.tag, create=args.create)

    print("\nDone! CI will now be able to download the model files.\n")


if __name__ == "__main__":
    main()
