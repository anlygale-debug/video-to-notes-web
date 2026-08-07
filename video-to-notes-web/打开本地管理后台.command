#!/bin/zsh

set -u

readonly PROJECT_ROOT="${0:A:h}"
readonly PYTHON="${PROJECT_ROOT}/.venv/bin/python"
readonly ADMIN_URL="http://127.0.0.1:4177/"

clear
echo "VIDEO / NOTES · 本地管理后台"
echo

if curl -fsS "${ADMIN_URL}" >/dev/null 2>&1; then
  echo "本地管理后台已经运行，正在打开……"
  open "${ADMIN_URL}"
  exit 0
fi

if [[ ! -x "${PYTHON}" ]]; then
  echo "本地 Python 环境尚未安装。"
  echo "请先在项目目录执行：python3 -m venv .venv"
  read -k 1 "?按任意键关闭。"
  exit 1
fi

export VTN_SESSION_SECRET="$(openssl rand -hex 32)"
export VTN_DATABASE_PATH="${PROJECT_ROOT}/data/vtn.sqlite3"
export VTN_LLM_PROVIDER_PATH="${PROJECT_ROOT}/data/settings.json"
export VTN_TRANSCRIPTION_PROVIDER_PATH="${PROJECT_ROOT}/data/transcription-provider.json"
export VTN_WHISPER_MODEL="${PROJECT_ROOT}/data/models/faster-whisper-tiny"

cd "${PROJECT_ROOT}"
"${PYTHON}" -m uvicorn invite_admin_app:app --host 127.0.0.1 --port 4177 &
server_pid=$!

stop_server() {
  if kill -0 "${server_pid}" >/dev/null 2>&1; then
    kill "${server_pid}" >/dev/null 2>&1
  fi
}

trap stop_server EXIT INT TERM

for attempt in {1..80}; do
  if ! kill -0 "${server_pid}" >/dev/null 2>&1; then
    wait "${server_pid}"
    exit $?
  fi
  if curl -fsS "${ADMIN_URL}" >/dev/null 2>&1; then
    echo "启动成功：${ADMIN_URL}"
    echo "关闭这个窗口或按 Control+C，即可停止后台。"
    open "${ADMIN_URL}"
    wait "${server_pid}"
    exit $?
  fi
  sleep 0.25
done

echo "启动超时，请保留这个窗口里的报错信息。"
stop_server
read -k 1 "?按任意键关闭。"
exit 1
