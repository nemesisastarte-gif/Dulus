# PyInstaller spec for the Dulus CLI binary.
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules("dulus_mcp")
    + collect_submodules("dulus_tools")
    + collect_submodules("gui")
    + ["dulus_gui", "customtkinter", "PIL", "playwright"]
)
datas = [
    ("sandbox/dist", "sandbox/dist"),
    ("data", "data"),
    ("skill/bundled", "skill/bundled"),
    ("brand-assets", "brand-assets"),
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
    name="nemesis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
