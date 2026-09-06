#!/bin/sh

launcher_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
launcher_path="$launcher_dir/$(basename -- "$0")"

if [ "${FLOWER_FIX_IN_TERMINAL:-0}" != "1" ] && [ ! -t 1 ]; then
    FLOWER_FIX_IN_TERMINAL=1
    export FLOWER_FIX_IN_TERMINAL
    if command -v konsole >/dev/null 2>&1; then
        exec konsole -e "$launcher_path" "$@"
    fi
    if command -v gnome-terminal >/dev/null 2>&1; then
        exec gnome-terminal -- "$launcher_path" "$@"
    fi
    if command -v kgx >/dev/null 2>&1; then
        exec kgx -- "$launcher_path" "$@"
    fi
    if command -v x-terminal-emulator >/dev/null 2>&1; then
        exec x-terminal-emulator -e "$launcher_path" "$@"
    fi
    if command -v xterm >/dev/null 2>&1; then
        exec xterm -e "$launcher_path" "$@"
    fi
    printf '%s\n' "Could not find a supported terminal emulator." >&2
    exit 1
fi

if [ ! -f "$launcher_dir/gyro_bridge/install_gyro_bridge.py" ]; then
    printf '%s\n' \
        "ERROR: Incomplete bundle. Extract the entire ZIP before running this launcher." \
        >&2
    exit_code=2
else
    cd "$launcher_dir" || exit 1
    python3 gyro_bridge/install_gyro_bridge.py install "$@"
    exit_code=$?
fi

printf '\nPress Enter to close...'
IFS= read -r _
printf '\n'
exit "$exit_code"
