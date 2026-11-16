#!/usr/bin/env bash
# 本地文件多标记交叉管理系统启动脚本（macOS / Linux）
set -e
cd "$(dirname "$0")"

if [ -n "$FM_PYTHON" ]; then
    PY="$FM_PYTHON"
elif command -v conda >/dev/null 2>&1 && conda env list | grep -q '^py311-pack '; then
    exec conda run --no-capture-output -n py311-pack python -m src.main
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    PY="python3"
fi

echo "使用解释器: $PY"
exec "$PY" -m src.main
