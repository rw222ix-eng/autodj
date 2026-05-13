# AutoDJ.spec
# -*- mode: python ; coding: utf-8 -*-
import platform
from PyInstaller.utils.hooks import collect_all, collect_submodules
from pathlib import Path

block_cipher = None

# Collect everything from the audio libraries — they have many AOT-compiled / data deps.
datas = []
binaries = []
hiddenimports = []

for pkg in ("librosa", "soundfile", "soxr", "audioread", "lazy_loader",
            "scipy", "sklearn", "numba", "llvmlite",
            "numpy", "fastapi", "uvicorn", "pydantic", "starlette",
            "python_multipart", "multipart", "anyio"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass  # package may not be installed (e.g., python_multipart vs multipart)

# Additional hidden imports that PyInstaller may miss
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.protocols",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "sklearn.utils._cython_blas",
    "sklearn.neighbors.typedefs",
    "sklearn.neighbors.quad_tree",
    "sklearn.tree._utils",
]

# Bundle frontend dist and samples as data files.
project_root = Path(SPECPATH).resolve().parent
frontend_dist = project_root / "frontend" / "dist"
samples_dir = project_root / "samples"
if frontend_dist.exists():
    for f in frontend_dist.rglob("*"):
        if f.is_file():
            rel_parent = str(f.relative_to(frontend_dist).parent).replace("\\", "/")
            datas.append((str(f), "frontend_dist/" + rel_parent))
if samples_dir.exists():
    for f in samples_dir.glob("*.wav"):
        datas.append((str(f), "samples"))

a = Analysis(
    ["autodj_main.py"],
    pathex=[str(project_root / "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6", "tkinter",
              "IPython", "jupyter", "notebook", "pytest", "mypy", "ruff", "black"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AutoDJ",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console open so user sees logs; can change to False later.
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# On macOS, wrap the executable in a .app bundle so it's double-clickable.
# PyInstaller ignores the BUNDLE directive on non-macOS platforms.
if platform.system() == "Darwin":
    app = BUNDLE(
        exe,
        name="AutoDJ.app",
        icon=None,
        bundle_identifier="com.autodj.app",
        info_plist={
            "CFBundleDisplayName": "AutoDJ",
            "CFBundleName": "AutoDJ",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
            "LSMinimumSystemVersion": "11.0",
        },
    )
