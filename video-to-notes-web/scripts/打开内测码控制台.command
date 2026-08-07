#!/bin/zsh

set -u

readonly SSH_KEY="/Users/yubo/.ssh/aliyun_hot"
readonly SSH_HOST="root@8.135.44.86"
readonly LOCAL_PORT="8768"
readonly REMOTE_PORT="8768"
readonly ADMIN_URL="http://127.0.0.1:${LOCAL_PORT}/"

clear
echo "VIDEO / NOTES · 内测码控制台"
echo
echo "正在建立 SSH 安全通道……"
echo "这个窗口保持打开时，管理页面才可使用。"
echo "关闭窗口即可断开管理通道。"
echo

if [[ ! -f "${SSH_KEY}" ]]; then
  echo "未找到服务器 SSH 密钥：${SSH_KEY}"
  echo "请按任意键关闭。"
  read -k 1
  exit 1
fi

if lsof -nP -iTCP:${LOCAL_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "本机端口 ${LOCAL_PORT} 已被占用，未启动新的安全通道。"
  echo "请关闭已有的内测码控制台窗口后重试。"
  echo "请按任意键关闭。"
  read -k 1
  exit 1
fi

ssh \
  -i "${SSH_KEY}" \
  -o BatchMode=yes \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -N \
  -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
  "${SSH_HOST}" &

tunnel_pid=$!

close_tunnel() {
  if kill -0 "${tunnel_pid}" >/dev/null 2>&1; then
    kill "${tunnel_pid}" >/dev/null 2>&1
  fi
}

trap close_tunnel EXIT INT TERM

for attempt in {1..40}; do
  if ! kill -0 "${tunnel_pid}" >/dev/null 2>&1; then
    wait "${tunnel_pid}"
    exit_code=$?
    echo
    echo "安全通道建立失败，SSH 返回状态：${exit_code}"
    echo "请按任意键关闭。"
    read -k 1
    exit "${exit_code}"
  fi
  if nc -z 127.0.0.1 "${LOCAL_PORT}" >/dev/null 2>&1; then
    echo "安全通道已连接，正在打开管理页面……"
    open "${ADMIN_URL}"
    echo
    echo "管理页面：${ADMIN_URL}"
    echo "可以最小化此窗口，但请不要关闭。"
    wait "${tunnel_pid}"
    exit $?
  fi
  sleep 0.2
done

echo "等待管理服务超时，请确认服务器服务状态。"
echo "请按任意键关闭。"
read -k 1
exit 1
