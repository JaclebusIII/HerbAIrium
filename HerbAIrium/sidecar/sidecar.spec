# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the HerbAIrium sidecar binary.

Build from the repo root:
    pyinstaller HerbAIrium/sidecar/sidecar.spec

Output: HerbAIrium/sidecar/dist/herbairium-sidecar  (or .exe on Windows)
"""

import sys
from pathlib import Path

pkg_root = Path(SPECPATH).parent    # …/HerbAIrium/  (contains models/, clients/, utils.py)
sidecar_dir = Path(SPECPATH)        # …/HerbAIrium/sidecar/

a = Analysis(
    [str(sidecar_dir / "server.py")],
    pathex=[str(pkg_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "clients",
        "clients.deepinfra_client",
        "models",
        "models.configuration",
        "models.metadata",
        "utils",
        # uvicorn internals that PyInstaller misses
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # PIL / Pillow extras for TIFF support
        "PIL._imaging",
        "PIL.TiffImagePlugin",
        "PIL.JpegImagePlugin",
        "PIL.PngImagePlugin",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "flet",
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "streamlit",
    ],
    noarchive=False,
    collect_all=["PIL"],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="herbairium-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for debugging; set False for production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
