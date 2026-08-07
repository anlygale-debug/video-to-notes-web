#!/bin/zsh
set -euo pipefail

project_root="${0:A:h:h}"
python="$project_root/.venv/bin/python"
model="$project_root/data/models/faster-whisper-tiny"

if [[ ! -x "$python" ]]; then
  print -u2 "本地 Python 环境尚未安装，请先在项目目录运行：python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f "$model/model.bin" ]]; then
  print -u2 "本地 faster-whisper Tiny 模型不完整：$model"
  exit 1
fi

export VTN_PAID_CALLS_ENABLED="${VTN_PAID_CALLS_ENABLED:-0}"
export VTN_WHISPER_MODEL="${VTN_WHISPER_MODEL:-$model}"

cd "$project_root"
exec "$python" -m uvicorn app:app \
  --host "${VTN_LOCAL_HOST:-127.0.0.1}" \
  --port "${VTN_LOCAL_PORT:-4176}"
