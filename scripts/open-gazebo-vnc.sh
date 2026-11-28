#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export DISPLAY="${DISPLAY:-:99}"
: "${GZ_PARTITION:?Set GZ_PARTITION to the Gazebo server partition before opening the GUI}"

vgl_root=${VGL_ROOT:-"$project_dir/.local/virtualgl"}
vgl_run=${VGL_RUN:-"$vgl_root/opt/VirtualGL/bin/vglrun"}
if [[ ! -x "$vgl_run" ]]; then
    vgl_run=$(command -v vglrun) || {
        echo 'VirtualGL was not found. Set VGL_ROOT to an unpacked VirtualGL directory.' >&2
        exit 1
    }
fi
if [[ "$vgl_run" == "$vgl_root"/opt/VirtualGL/* ]]; then
    export LD_LIBRARY_PATH="$vgl_root/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

existing=$(xwininfo -root -tree | awk '/"Gazebo Sim":.*gz-sim-gui/ {print $1}')
env -u LIBGL_ALWAYS_SOFTWARE "$vgl_run" -d egl gz sim -g \
    --render-engine-gui ogre2 --gui-config "$project_dir/config/gazebo-vnc-fullscreen.config" &
gui_pid=$!
trap 'kill -INT "$gui_pid" 2>/dev/null || true' INT TERM
for attempt in {1..45}; do
    kill -0 "$gui_pid" 2>/dev/null || break
    window=$(xwininfo -root -tree | awk -v existing="$existing" '
        /"Gazebo Sim":.*gz-sim-gui/ && index("\n" existing "\n", "\n" $1 "\n") == 0 {print $1; exit}')
    if [[ -n "$window" ]]; then
        python3 - "$window" <<'PY'
import ctypes as c
import sys

x11 = c.CDLL("libX11.so.6")
x11.XOpenDisplay.argtypes = [c.c_char_p]
x11.XOpenDisplay.restype = c.c_void_p
display = x11.XOpenDisplay(None)
if not display:
    raise SystemExit("Cannot open VNC display")
x11.XDefaultScreen.argtypes = [c.c_void_p]
screen = x11.XDefaultScreen(display)
for name in ("XDisplayWidth", "XDisplayHeight"):
    getattr(x11, name).argtypes = [c.c_void_p, c.c_int]
width = x11.XDisplayWidth(display, screen)
height = x11.XDisplayHeight(display, screen)
x11.XMoveResizeWindow.argtypes = [
    c.c_void_p, c.c_ulong, c.c_int, c.c_int, c.c_uint, c.c_uint,
]
x11.XMoveResizeWindow(display, int(sys.argv[1], 16), 0, 0, width, height)
x11.XSync.argtypes = [c.c_void_p, c.c_int]
x11.XSync(display, 0)
PY
        break
    fi
    sleep 1
done
wait "$gui_pid"
