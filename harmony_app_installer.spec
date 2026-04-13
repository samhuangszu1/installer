# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['harmony_ultra_modern.py'],
    pathex=[],
    binaries=[
        ('hdc_win/hdc_w.exe', 'hdc_win'),
        ('hdc_win/libusb_shared.dll', 'hdc_win'),
        ('hdc_arm/hdc', 'hdc_arm'),
        ('hdc_x86/hdc_x86', 'hdc_x86'),
    ],
    datas=[
        ('hdc_win/*', 'hdc_win'),
        ('hdc_arm/*', 'hdc_arm'),
        ('hdc_x86/*', 'hdc_x86'),
        ('logo.ico', '.'),
        ('logo.png', '.')
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'requests',
        'urllib.parse',
        'json',
        'threading',
        'subprocess',
        'platform',
        'time',
        'pathlib',
        'os',
        'sys'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HarmonyOSInstaller2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico']
)
