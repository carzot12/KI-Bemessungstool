# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


project_root = Path(SPECPATH)
is_macos = sys.platform == "darwin"
is_windows = sys.platform == "win32"

if not (is_macos or is_windows):
    raise RuntimeError("Diese Spec unterstützt derzeit macOS und Windows.")

datas = [
    (str(project_root / "assets" / "logo.png"), "assets"),
    (
        str(project_root / "infopol" / "materials" / "timber.json"),
        "infopol/materials",
    ),
    (
        str(project_root / "ai" / "prompts" / "stabduebel_system.txt"),
        "ai/prompts",
    ),
]

a = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=["openai"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [] if is_macos else a.binaries,
    [] if is_macos else a.datas,
    [],
    exclude_binaries=is_macos,
    name="KI-Bemessungstool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=(
        str(project_root / "assets" / "app_icon.icns")
        if is_macos
        else str(project_root / "assets" / "app_icon.ico")
    ),
    codesign_identity=None,
    entitlements_file=None,
)

if is_macos:
    collect = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="KI-Bemessungstool",
    )

    app = BUNDLE(
        collect,
        name="KI-Bemessungstool.app",
        icon=str(project_root / "assets" / "app_icon.icns"),
        bundle_identifier="at.holzbauforschung.ki-bemessungstool",
        version="1.0.0",
        info_plist={
            "CFBundleDisplayName": "KI-Bemessungstool",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
        },
    )
