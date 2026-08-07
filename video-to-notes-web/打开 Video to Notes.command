#!/bin/zsh

set -u

readonly PROJECT_ROOT="${0:A:h}"
readonly APP_URL="http://127.0.0.1:4176/video-notes"
readonly HEALTH_URL="http://127.0.0.1:4176/api/health"

clear
echo "VIDEO / NOTES · 本地版"
echo

if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
  echo "本地服务已经运行，正在打开产品页面……"
  open "${APP_URL}"
  exit 0
fi

if ! lsof -nP -iTCP:8082 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "提示：免费 AI 线路尚未启动。"
  echo "需要生成笔记时，请先双击桌面的 NVIDIA-代理.command。"
  echo
fi

echo "正在启动本地服务……"
echo "关闭这个窗口或按 Control+C，即可停止服务。"
echo

"${PROJECT_ROOT}/scripts/run-local.sh" &
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
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    echo "启动成功：${APP_URL}"
    open "${APP_URL}"
    wait "${server_pid}"
    exit $?
  fi
  sleep 0.25
done

echo "启动超时，请保留这个窗口里的报错信息。"
stop_server
read -k 1 "?按任意键关闭。"
exit 1
