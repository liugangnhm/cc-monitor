"""Build script for packaging into exe."""

import subprocess
import sys
from pathlib import Path


def build():
    project_root = Path(__file__).resolve().parent.parent.parent
    main_py = project_root / "src" / "cc_monitor" / "main.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "cc-monitor",
        "--windowed",
        "--onefile",
        "--clean",
        str(main_py),
    ]

    print(f"Building cc-monitor.exe from {main_py} ...")
    result = subprocess.run(cmd, cwd=str(project_root))
    if result.returncode == 0:
        exe_path = project_root / "dist" / "cc-monitor.exe"
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"\nDone! {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"\nBuild failed with exit code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
