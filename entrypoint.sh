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

# ── Graceful shutdown handler ─────────────────────────────────────
_shutdown() {
    echo "[entrypoint] Received shutdown signal — stopping Python process..."
    kill -TERM "$CHILD_PID" 2>/dev/null || true
    wait "$CHILD_PID" 2>/dev/null || true
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
