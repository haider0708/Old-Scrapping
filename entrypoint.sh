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

# ── Start Tor if USE_TOR is enabled ───────────────────────────────
if [ "${USE_TOR:-0}" = "1" ] && command -v tor &>/dev/null; then
    TOR_PASSWORD="${TOR_PASSWORD:-retails}"
    TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
    TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
    TOR_DATA_DIR="/tmp/tor"
    mkdir -p "$TOR_DATA_DIR"

    HASHED_PASS=$(tor --hash-password "$TOR_PASSWORD" | tail -1)

    cat > /tmp/torrc <<TOREOF
SocksPort ${TOR_SOCKS_PORT}
ControlPort ${TOR_CONTROL_PORT}
HashedControlPassword ${HASHED_PASS}
DataDirectory ${TOR_DATA_DIR}
Log notice stderr
TOREOF

    tor -f /tmp/torrc &
    TOR_PID=$!
    echo "[entrypoint] Tor starting (PID ${TOR_PID})..."
    # Wait for Tor to bootstrap (connect to the network)
    sleep 10
    echo "[entrypoint] Tor ready on SOCKS=${TOR_SOCKS_PORT}, Control=${TOR_CONTROL_PORT}"
elif [ "${USE_TOR:-0}" = "1" ]; then
    echo "[entrypoint] WARNING: USE_TOR=1 but tor binary not found!"
fi

# ── Graceful shutdown handler ─────────────────────────────────────
_shutdown() {
    echo "[entrypoint] Received shutdown signal — stopping Python process..."
    kill -TERM "$CHILD_PID" 2>/dev/null || true
    wait "$CHILD_PID" 2>/dev/null || true
    if [ -n "${TOR_PID:-}" ]; then
        kill -TERM "$TOR_PID" 2>/dev/null || true
    fi
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
