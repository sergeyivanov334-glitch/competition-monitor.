"""Сборка desktop-приложения: PyInstaller -> competitionmonitor.exe."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "desktop" / "competitionmonitor.spec"
EXE = ROOT / "desktop" / "dist" / "competitionmonitor" / "competitionmonitor.exe"


def main() -> None:
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(SPEC),
            "--noconfirm",
            "--distpath",
            str(ROOT / "desktop" / "dist"),
            "--workpath",
            str(ROOT / "desktop" / "build"),
        ]
    )
    print(f"Готово: {EXE}")


if __name__ == "__main__":
    main()
