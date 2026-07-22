# PyInstaller spec for the Dulus CLI binary.
from PyInstaller.utils.hooks import collect_submodules, collect_all

_wasmtime_datas, _wasmtime_binaries, _wasmtime_hidden = collect_all("wasmtime")
hiddenimports = (
    collect_submodules("dulus_mcp")
    + collect_submodules("dulus_tools")
    + collect_submodules("gui")
    + _wasmtime_hidden
    + ["dulus_gui", "customtkinter", "PIL", "PIL._tkinter_finder", "PIL._imagingtk", "playwright", "wasmtime"]
)

binaries = _wasmtime_binaries
datas = _wasmtime_datas + [
    ("sandbox/dist", "sandbox/dist"),
    ("data", "data"),
    ("skill/bundled", "skill/bundled"),
    ("brand-assets", "brand-assets"),
    ("sha3_wasm_bg.wasm", "."),
]

a = Analysis(
    ["dulus.py"],
    pathex=["."],
    binaries=binaries,
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
