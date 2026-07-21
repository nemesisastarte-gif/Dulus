# PyInstaller spec for the Dulus CLI binary.
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("dulus_mcp") + collect_submodules("dulus_tools")
datas = [
    ("sandbox/dist", "sandbox/dist"),
    ("data", "data"),
    ("skill/bundled", "skill/bundled"),
    ("sha3_wasm_bg.wasm", "."),
]

a = Analysis(
    ["dulus.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dulus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
