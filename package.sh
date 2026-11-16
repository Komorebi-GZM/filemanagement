#!/usr/bin/env bash
# 文件管理系统打包脚本（macOS / Linux），产物输出到 dist_new/
set -e
cd "$(dirname "$0")"

echo "开始打包文件管理系统..."
if command -v conda >/dev/null 2>&1 && conda env list | grep -q '^py311-pack '; then
    conda run --no-capture-output -n py311-pack pyinstaller filemanagement.spec --noconfirm --distpath dist_new
else
    pyinstaller filemanagement.spec --noconfirm --distpath dist_new
fi
echo "打包完成！产物位于 dist_new 目录"
