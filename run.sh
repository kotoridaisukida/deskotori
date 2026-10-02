#!/usr/bin/env bash
# 启动抢镜鸟。没有虚拟环境时会自动建一个并安装依赖。
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
if [[ ! -x .venv/bin/python ]]; then
  "$PY" -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python main.py "$@"
