# -*- mode: python ; coding: utf-8 -*-
"""Сборка Competition Monitor в папку с competitionmonitor.exe."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project = Path(SPECPATH).resolve().parent
hiddenimports = collect_submodules("backend") + collect_submodules("selenium") + ["tasks"]

a = Analysis(
    [str(project / "desktop" / "app.py")],
    pathex=[str(project), str(project / "desktop")],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pytest", "playwright"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="competitionmonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="competitionmonitor",
)
