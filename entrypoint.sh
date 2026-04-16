#!/bin/bash
# entrypoint.sh — container startup script
# Starts a virtual display (Xvfb) so Playwright's --headless=new works
# inside a headless container, then hands off to the Python process.
# tini (PID 1) handles SIGTERM/SIGINT forwarding and zombie reaping.

set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-99}"
export DISPLAY=":${DISPLAY_NUM}"

# ── Start virtual display if Xvfb is available ────────────────────
if command -v Xvfb &>/dev/null; then
    Xvfb ":${DISPLAY_NUM}" -screen 0 1280x1024x24 -ac +extension GLX +render -noreset &
    XVFB_PID=$!
    # Wait briefly for Xvfb to be ready
    sleep 0.5
    echo "[entrypoint] Xvfb started on DISPLAY=${DISPLAY} (PID ${XVFB_PID})"
else
    echo "[entrypoint] Xvfb not found — running without virtual display"
fi

# ── Start Tor pool if USE_TOR is enabled ──────────────────────────
TOR_PIDS=""
if [ "${USE_TOR:-0}" = "1" ] && command -v tor &>/dev/null; then
    TOR_PASSWORD="${TOR_PASSWORD:-retails}"
    TOR_BASE_SOCKS="${TOR_SOCKS_PORT:-9050}"
    TOR_BASE_CONTROL="${TOR_CONTROL_PORT:-9051}"
    TOR_NUM="${TOR_INSTANCES:-8}"

    HASHED_PASS=$(tor --hash-password "$TOR_PASSWORD" | tail -1)

    for i in $(seq 0 $((TOR_NUM - 1))); do
        SOCKS_PORT=$((TOR_BASE_SOCKS + i * 2))
        CTRL_PORT=$((TOR_BASE_CONTROL + i * 2))
        DATA_DIR="/tmp/tor/instance_${i}"
        mkdir -p "$DATA_DIR"

        cat > "/tmp/torrc_${i}" <<TOREOF
SocksPort ${SOCKS_PORT}
ControlPort ${CTRL_PORT}
HashedControlPassword ${HASHED_PASS}
DataDirectory ${DATA_DIR}
Log warn stderr
TOREOF

        tor -f "/tmp/torrc_${i}" &
        TOR_PIDS="${TOR_PIDS} $!"
        echo "[entrypoint] Tor instance ${i}: SOCKS=${SOCKS_PORT} Control=${CTRL_PORT}"
    done

    echo "[entrypoint] Waiting for ${TOR_NUM} Tor instances to bootstrap..."
    sleep 15
    echo "[entrypoint] Tor pool ready (${TOR_NUM} instances)"
elif [ "${USE_TOR:-0}" = "1" ]; then
    echo "[entrypoint] WARNING: USE_TOR=1 but tor binary not found!"
fi

# ── Graceful shutdown handler ─────────────────────────────────────
_shutdown() {
    echo "[entrypoint] Received shutdown signal — stopping Python process..."
    kill -TERM "$CHILD_PID" 2>/dev/null || true
    wait "$CHILD_PID" 2>/dev/null || true
    for pid in $TOR_PIDS; do
        kill -TERM "$pid" 2>/dev/null || true
    done
    if [ -n "${XVFB_PID:-}" ]; then
        kill -TERM "$XVFB_PID" 2>/dev/null || true
    fi
    echo "[entrypoint] Clean exit."
    exit 0
}
trap _shutdown SIGTERM SIGINT

# ── Launch the application ────────────────────────────────────────
echo "[entrypoint] Starting: $*"
"$@" &
CHILD_PID=$!

# Wait for the child, forwarding any signals
wait "$CHILD_PID"
EXIT_CODE=$?

echo "[entrypoint] Process exited with code ${EXIT_CODE}"
exit $EXIT_CODE
