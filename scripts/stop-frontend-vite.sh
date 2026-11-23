#!/usr/bin/env bash

set -u

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P) || exit 1
vite_link="$root/frontend/node_modules/.bin/vite"
vite_entry=$(readlink -f -- "$vite_link") || {
  echo "找不到 Vite：$vite_link。請先安裝前端依賴。" >&2
  exit 1
}
if [[ ! -f "$vite_entry" ]]; then
  echo "找不到 Vite：$vite_link。請先安裝前端依賴。" >&2
  exit 1
fi

is_project_vite() {
  local pid=$1 exe cwd script
  local -a args
  [[ -O "/proc/$pid" ]] || return 1
  exe=$(readlink -f -- "/proc/$pid/exe" 2>/dev/null) || return 1
  [[ "${exe##*/}" == node || "${exe##*/}" == nodejs ]] || return 1
  mapfile -d '' -t args < "/proc/$pid/cmdline" 2>/dev/null || return 1
  (( ${#args[@]} >= 2 )) || return 1
  script=${args[1]}
  if [[ "$script" != /* ]]; then
    cwd=$(readlink -f -- "/proc/$pid/cwd" 2>/dev/null) || return 1
    script="$cwd/$script"
  fi
  script=$(readlink -f -- "$script" 2>/dev/null) || return 1
  [[ "$script" == "$vite_entry" ]]
}

declare -a pids=()
for process in /proc/[0-9]*; do
  pid=${process##*/}
  if is_project_vite "$pid"; then
    pids+=("$pid")
  fi
done

if (( ${#pids[@]} == 0 )); then
  echo "目前帳號沒有本專案的 Vite Node 程序。"
  exit 0
fi

failed=0
for pid in "${pids[@]}"; do
  if is_project_vite "$pid"; then
    echo "停止本專案的 Vite Node 程序：PID $pid"
    if ! kill -TERM "$pid"; then
      echo "無法停止 PID $pid。" >&2
      failed=1
    fi
  fi
done

for pid in "${pids[@]}"; do
  for ((attempt = 0; attempt < 50; attempt++)); do
    is_project_vite "$pid" || break
    sleep 0.1
  done
  if is_project_vite "$pid"; then
    echo "PID $pid 尚未結束；請手動檢查。" >&2
    failed=1
  fi
done

if (( failed )); then
  exit 1
fi
echo "已停止找到的本專案 Vite Node 程序。"
