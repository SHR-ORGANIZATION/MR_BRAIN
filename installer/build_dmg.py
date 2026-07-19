#!/usr/bin/env python3
"""
AMAZON AI - macOS DMG Builder
Creates a polished .dmg installer with drag-to-install layout.

Usage:
    python installer/build_dmg.py              # Build DMG from existing .app
    python installer/build_dmg.py --background # Use custom background (optional)
"""
import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
APP_NAME = "AMAZON AI"
DMG_NAME = "AMAZON_AI_Installer.dmg"
DMG_VOLUME_NAME = "AMAZON AI"


def find_app():
    app_path = DIST_DIR / f"{APP_NAME}.app"
    if not app_path.exists():
        print(f"✗ App bundle not found: {app_path}")
        print("  Run 'python build_installer.py' first to build the .app")
        sys.exit(1)
    return app_path


def create_dmg_background(width=660, height=400):
    """Create a simple DMG background image using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new('RGB', (width, height), color='#f5f5f7')
        draw = ImageDraw.Draw(img)

        # Subtle gradient header
        for y in range(80):
            alpha = int(255 * (1 - y / 80))
            draw.line([(0, y), (width, y)], fill=(220, 220, 225))

        # Title text
        try:
            font = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 28)
            small_font = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 14)
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        # Center title
        bbox = draw.textbbox((0, 0), "Drag AMAZON AI to Applications", font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(((width - text_w) // 2, 25), "Drag AMAZON AI to Applications",
                  fill='#333333', font=font)

        # Arrow indicator
        arrow_y = height // 2
        draw.text((width // 2 - 5, arrow_y - 20), "→", fill='#10a37f', font=font)

        # Footer
        bbox2 = draw.textbbox((0, 0), "AMAZON AI v1.0.0", font=small_font)
        text_w2 = bbox2[2] - bbox2[0]
        draw.text(((width - text_w2) // 2, height - 40), "AMAZON AI v1.0.0",
                  fill='#888888', font=small_font)

        bg_path = DIST_DIR / "dmg_background.png"
        img.save(str(bg_path))
        return bg_path

    except ImportError:
        print("  Pillow not available, using default DMG background")
        return None


def build_dmg(app_path, compressed=True):
    """Build the DMG file."""
    dmg_path = DIST_DIR / DMG_NAME

    # Remove old DMG
    if dmg_path.exists():
        dmg_path.unlink()
        print(f"  Removed old {DMG_NAME}")

    # Create staging directory
    staging = DIST_DIR / "_dmg_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    # Copy .app
    dest_app = staging / f"{APP_NAME}.app"
    print(f"  Copying {APP_NAME}.app...")
    shutil.copytree(str(app_path), str(dest_app), symlinks=True)

    # Create /Applications symlink
    apps_link = staging / "Applications"
    if not apps_link.exists():
        os.symlink("/Applications", str(apps_link))

    # Build DMG
    dmg_format = "UDBZ" if compressed else "UDRO"
    print(f"  Creating DMG ({'compressed' if compressed else 'uncompressed'})...")

    try:
        result = subprocess.run([
            "hdiutil", "create",
            "-volname", DMG_VOLUME_NAME,
            "-srcfolder", str(staging),
            "-ov",
            "-format", dmg_format,
            str(dmg_path),
        ], check=True, capture_output=True, text=True)

        size_mb = dmg_path.stat().st_size / (1024 * 1024)
        print(f"\n✓ DMG created successfully!")
        print(f"  Path: {dmg_path}")
        print(f"  Size: {size_mb:.1f} MB")

    except subprocess.CalledProcessError as e:
        print(f"✗ DMG creation failed: {e.stderr}")
        sys.exit(1)

    finally:
        # Cleanup staging
        if staging.exists():
            shutil.rmtree(staging)


def codesign_if_possible(app_path):
    """Attempt to codesign the app (requires Developer ID)."""
    try:
        # Check if any signing identity is available
        result = subprocess.run(
            ["security", "find-identity", "-v", "-p", "codesigning"],
            capture_output=True, text=True
        )
        if "Developer ID Application" in result.stdout:
            print("  Signing app with Developer ID...")
            subprocess.run([
                "codesign", "--deep", "--force", "--sign",
                "Developer ID Application",
                "--options", "runtime",  # Hardened runtime
                str(app_path),
            ], check=True, capture_output=True)
            print("  ✓ App signed")
        else:
            print("  ℹ No Developer ID found - skipping codesign")
            print("    (App will work but show 'unidentified developer' warning)")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Build AMAZON AI macOS DMG")
    parser.add_argument("--uncompressed", action="store_true", help="Create uncompressed DMG (faster)")
    parser.add_argument("--sign", action="store_true", help="Attempt to codesign the app")
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  AMAZON AI - macOS DMG Builder")
    print("=" * 50 + "\n")

    app_path = find_app()
    print(f"  Found app: {app_path}\n")

    if args.sign:
        codesign_if_possible(app_path)

    build_dmg(app_path, compressed=not args.uncompressed)

    print(f"\nDone! DMG ready at: {DIST_DIR / DMG_NAME}\n")


if __name__ == "__main__":
    main()
