# -*- mode: python ; coding: utf-8 -*-
"""Сборка десктопного приложения в папку с CompetitorAI.exe."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

project = Path(SPECPATH).resolve().parent
datas = []
binaries = []
hiddenimports = collect_submodules("backend")

driver_data, driver_binaries, driver_hidden = collect_all("playwright")
datas += driver_data
binaries += driver_binaries
hiddenimports += driver_hidden

a = Analysis(
    [str(project / "desktop" / "app.py")],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CompetitorAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CompetitorAI",
)
