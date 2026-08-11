#!/bin/zsh

set -u

readonly PROJECT_ROOT="/Users/yubo/Claude code test/video-to-notes-web"
readonly YTDLP="${PROJECT_ROOT}/.venv/bin/yt-dlp"
readonly SSH_KEY="/Users/yubo/.ssh/aliyun_hot"
readonly SSH_HOST="root@8.135.44.86"
readonly REMOTE_COOKIE_PATH="/var/lib/video-to-notes/douyin-cookies.txt"
readonly PROBE_URL="https://www.douyin.com/video/7253815894357363979"

clear
echo "VIDEO / NOTES · 更新服务器抖音解析凭证"
echo
echo "这个工具只会上传 douyin.com 域名下的 Cookie。"
echo "其他网站 Cookie 和浏览器密码不会上传。"
echo

if [[ ! -x "${YTDLP}" ]]; then
  echo "未找到项目内的 yt-dlp：${YTDLP}"
  read -k 1 "?按任意键关闭。"
  exit 1
fi

if [[ ! -f "${SSH_KEY}" ]]; then
  echo "未找到服务器 SSH 密钥：${SSH_KEY}"
  read -k 1 "?按任意键关闭。"
  exit 1
fi

open -a "Google Chrome" "https://www.douyin.com/"
echo "请在 Chrome 中等待抖音首页正常显示。"
echo "如果出现验证码，请先完成验证。"
echo
read -k 1 "?确认首页已正常显示后，按任意键继续……"
echo

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/vtn-douyin-cookie.XXXXXX")"
chmod 700 "${temp_dir}"
all_cookies="${temp_dir}/all-cookies.txt"
douyin_cookies="${temp_dir}/douyin-cookies.txt"

cleanup() {
  rm -rf "${temp_dir}"
}
trap cleanup EXIT INT TERM

echo "正在从 Chrome 读取最新抖音访问凭证……"
"${YTDLP}" \
  --cookies-from-browser chrome \
  --cookies "${all_cookies}" \
  --skip-download \
  --simulate \
  --no-warnings \
  "${PROBE_URL}" >/dev/null 2>&1 || true

if [[ ! -s "${all_cookies}" ]]; then
  echo "没有从 Chrome 读取到 Cookie。请确认抖音首页已正常打开后重试。"
  read -k 1 "?按任意键关闭。"
  exit 1
fi

awk -F '\t' '
  BEGIN {
    print "# Netscape HTTP Cookie File"
    print "# Only Douyin cookies are included"
  }
  /^#HttpOnly_/ {
    domain=$1
    sub(/^#HttpOnly_/, "", domain)
    if (domain ~ /(^|\.)douyin\.com$/) print $0
    next
  }
  /^#/ { next }
  NF >= 7 {
    domain=$1
    if (domain ~ /(^|\.)douyin\.com$/) print $0
  }
' "${all_cookies}" > "${douyin_cookies}"
chmod 600 "${douyin_cookies}"

if ! awk -F '\t' '$6 == "s_v_web_id" { found=1 } END { exit !found }' "${douyin_cookies}"; then
  echo "Chrome 中没有找到有效的抖音匿名访问凭证。"
  echo "请刷新抖音首页，等待页面内容出现后再运行一次。"
  read -k 1 "?按任意键关闭。"
  exit 1
fi

echo "正在安全上传到服务器……"
scp \
  -i "${SSH_KEY}" \
  -o BatchMode=yes \
  "${douyin_cookies}" \
  "${SSH_HOST}:/tmp/vtn-douyin-cookies.next" >/dev/null

ssh \
  -i "${SSH_KEY}" \
  -o BatchMode=yes \
  "${SSH_HOST}" \
  "install -o vtn -g vtn -m 600 /tmp/vtn-douyin-cookies.next '${REMOTE_COOKIE_PATH}' && \
   rm -f /tmp/vtn-douyin-cookies.next && \
   if grep -q '^VTN_DOUYIN_COOKIES_PATH=' /etc/video-to-notes.env; then \
     sed -i 's#^VTN_DOUYIN_COOKIES_PATH=.*#VTN_DOUYIN_COOKIES_PATH=${REMOTE_COOKIE_PATH}#' /etc/video-to-notes.env; \
   else \
     printf '\nVTN_DOUYIN_COOKIES_PATH=${REMOTE_COOKIE_PATH}\n' >> /etc/video-to-notes.env; \
   fi && \
   systemctl restart video-to-notes && \
   sleep 4 && \
   systemctl is-active --quiet video-to-notes"

if [[ $? -ne 0 ]]; then
  echo "服务器更新失败，请保留这个窗口里的报错信息。"
  read -k 1 "?按任意键关闭。"
  exit 1
fi

echo
echo "更新完成。现在可以回到网页重新解析刚才的抖音链接。"
read -k 1 "?按任意键关闭。"
