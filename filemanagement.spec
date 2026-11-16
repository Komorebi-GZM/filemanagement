# PyInstaller spec file for 文件管理系统（Windows / macOS）
import sys

block_cipher = None

added_files = [
    ('config/config.ini', 'config'),
    ('src/app/db/schema.sql', 'src/app/db'),
]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
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

# 修改输出目录，避免权限冲突
dist_dir = 'dist_new'

# 确保输出目录存在
import os
if not os.path.exists(dist_dir):
    os.makedirs(dist_dir)

if sys.platform == 'darwin':
    # macOS：onedir + .app 包（onefile 窗口应用在 macOS 上已被 PyInstaller 弃用）
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='文件管理系统',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        target_arch=None,  # 如需通用包可改为 'universal2'
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='文件管理系统',
    )
    app = BUNDLE(
        coll,
        name='文件管理系统.app',
        icon=None,
        bundle_identifier='com.komorebi.filemanagement',
        info_plist={'NSHighResolutionCapable': True},
    )
else:
    executable = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='文件管理系统',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # 设置为False以隐藏控制台窗口
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,  # 可以添加图标文件路径
        distpath=dist_dir,
    )
