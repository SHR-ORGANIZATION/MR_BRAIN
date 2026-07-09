#!/usr/bin/env python3
"""
AMAZON AI - Cross-Platform Installer Builder
Builds native installers for macOS (.app / .dmg) and Windows (.exe / installer)

Usage:
    python build_installer.py              # Auto-detect OS and build
    python build_installer.py --mac        # Force macOS build
    python build_installer.py --windows    # Force Windows build (run on Windows)
    python build_installer.py --no-model   # Skip ML model (smaller installer)
    python build_installer.py --dmg        # Also create DMG (macOS only)
"""
import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "amazon_ai.spec"

# ─── ANSI Colors ─────────────────────────────────────────────────────────────
class C:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    END    = "\033[0m"

def log(msg, color=C.GREEN):
    print(f"{color}{msg}{C.END}")

def error(msg):
    log(f"✗ {msg}", C.RED)
    sys.exit(1)

def warn(msg):
    log(f"⚠ {msg}", C.YELLOW)

# ─── Pre-flight checks ───────────────────────────────────────────────────────
def check_requirements():
    log("\n🔍 Checking requirements...\n", C.CYAN)

    # Python version
    py_ver = sys.version_info
    log(f"  Python: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 8):
        error("Python 3.8+ is required")

    # PyInstaller
    try:
        import PyInstaller
        log(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        error("PyInstaller not found. Install with: pip install pyinstaller")

    # Check key dependencies
    missing = []
    for pkg in ['customtkinter', 'PIL', 'torch', 'transformers', 'psutil']:
        try:
            __import__(pkg)
            log(f"  {pkg}: ✓")
        except ImportError:
            missing.append(pkg)
            warn(f"  {pkg}: NOT FOUND")

    if missing:
        warn(f"\n  Missing packages: {', '.join(missing)}")
        warn("  Install all deps with: pip install -r requirements.txt")
        resp = input("\n  Continue anyway? (y/N): ").strip().lower()
        if resp != 'y':
            sys.exit(0)

    # Platform
    platform = sys.platform
    if platform == 'darwin':
        log(f"  Platform: macOS ({os.uname().machine})")
    elif platform == 'win32':
        log(f"  Platform: Windows")
    else:
        log(f"  Platform: {platform}")

    log("\n✓ All checks passed\n", C.GREEN)


# ─── Clean previous builds ────────────────────────────────────────────────────
def clean_build():
    log("🧹 Cleaning previous builds...\n", C.CYAN)
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
            log(f"  Removed {d.name}/")
    log("  Done\n")


# ─── Run PyInstaller ──────────────────────────────────────────────────────────
def run_pyinstaller():
    log("📦 Building with PyInstaller...\n", C.CYAN)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--noconfirm",
        "--clean",
    ]

    log(f"  Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        error("PyInstaller build failed!")

    log("\n✓ Build complete\n", C.GREEN)


# ─── macOS DMG creation ──────────────────────────────────────────────────────
def create_dmg():
    if sys.platform != 'darwin':
        warn("DMG creation is only available on macOS")
        return

    log("💿 Creating macOS DMG...\n", C.CYAN)

    app_path = DIST_DIR / "AMAZON AI.app"
    dmg_path = DIST_DIR / "AMAZON_AI_Installer.dmg"

    if not app_path.exists():
        error(f"App bundle not found at {app_path}")

    # Remove old DMG
    if dmg_path.exists():
        dmg_path.unlink()

    # Create temporary DMG source directory
    dmg_src = DIST_DIR / "dmg_temp"
    dmg_src.mkdir(exist_ok=True)

    # Copy .app to dmg source
    shutil.copytree(str(app_path), str(dmg_src / "AMAZON AI.app"), symlinks=True)

    # Create symlink to /Applications for drag-install
    apps_link = dmg_src / "Applications"
    if not apps_link.exists():
        os.symlink("/Applications", str(apps_link))

    # Create DMG
    try:
        subprocess.run([
            "hdiutil", "create",
            "-volname", "AMAZON AI",
            "-srcfolder", str(dmg_src),
            "-ov",
            "-format", "UDBZ",   # Compressed DMG
            str(dmg_path),
        ], check=True, capture_output=True)
        log(f"\n✓ DMG created: {dmg_path}")
        size_mb = dmg_path.stat().st_size / (1024 * 1024)
        log(f"  Size: {size_mb:.1f} MB\n")
    except subprocess.CalledProcessError as e:
        warn(f"DMG creation failed: {e}")
    finally:
        # Clean up temp
        if dmg_src.exists():
            shutil.rmtree(dmg_src)


# ─── Windows installer info ───────────────────────────────────────────────────
def windows_installer_info():
    if sys.platform != 'win32':
        return

    exe_path = DIST_DIR / "AMAZON AI.exe"
    if not exe_path.exists():
        warn("Windows .exe not found in dist/")
        return

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    log(f"\n✓ Windows executable ready: {exe_path}")
    log(f"  Size: {size_mb:.1f} MB")
    log(f"\n  To create a proper Windows installer (.exe setup):")
    log(f"  1. Download Inno Setup: https://jrsoftware.org/isdl.php")
    log(f"  2. Open: installer/windows_setup.iss")
    log(f"  3. Click 'Build' → generates AMAZON_AI_Setup.exe\n")


# ─── Summary ──────────────────────────────────────────────────────────────────
def print_summary():
    log("\n" + "=" * 60, C.CYAN)
    log("  AMAZON AI - Build Summary", C.CYAN)
    log("=" * 60 + "\n", C.CYAN)

    if sys.platform == 'darwin':
        app_path = DIST_DIR / "AMAZON AI.app"
        dmg_path = DIST_DIR / "AMAZON_AI_Installer.dmg"
        if app_path.exists():
            size_mb = app_path.stat().st_size / (1024 * 1024)
            log(f"  ✓ macOS App:  {app_path}")
            log(f"    Size: {size_mb:.1f} MB")
        if dmg_path.exists():
            size_mb = dmg_path.stat().st_size / (1024 * 1024)
            log(f"  ✓ DMG:        {dmg_path}")
            log(f"    Size: {size_mb:.1f} MB")

    elif sys.platform == 'win32':
        exe_path = DIST_DIR / "AMAZON AI.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            log(f"  ✓ Windows EXE: {exe_path}")
            log(f"    Size: {size_mb:.1f} MB")

    log(f"\n  Output directory: {DIST_DIR}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Build AMAZON AI installer")
    parser.add_argument("--mac", action="store_true", help="Build for macOS")
    parser.add_argument("--windows", action="store_true", help="Build for Windows")
    parser.add_argument("--dmg", action="store_true", help="Create DMG (macOS only)")
    parser.add_argument("--no-clean", action="store_true", help="Skip cleaning previous builds")
    args = parser.parse_args()

    log("\n" + "=" * 60, C.BOLD)
    log("  AMAZON AI - Installer Builder", C.BOLD)
    log("=" * 60, C.BOLD)

    check_requirements()

    if not args.no_clean:
        clean_build()

    run_pyinstaller()

    # Post-build steps
    if sys.platform == 'darwin' and args.dmg:
        create_dmg()

    if sys.platform == 'win32':
        windows_installer_info()

    print_summary()

    log("Done! 🎉\n", C.GREEN)


if __name__ == "__main__":
    main()
