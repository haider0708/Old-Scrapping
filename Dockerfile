# syntax=docker/dockerfile:1
# ──────────────────────────────────────────────────────────────────
# Stage 1 – dependency builder (keeps final image lean)
# ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install -r requirements.txt

# ──────────────────────────────────────────────────────────────────
# Stage 2 – runtime image
# ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # Playwright will look here for browsers
    PLAYWRIGHT_BROWSERS_PATH=/pw-browsers \
    # Suppress ResourceWarning noise from asyncio transports on exit
    PYTHONWARNINGS=ignore::ResourceWarning

# ── System libraries required by Playwright Chromium ──────────────
# Plus Xvfb so `headless=False --headless=new` works inside a
# container (no real display needed, Xvfb provides a virtual one).
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Chromium runtime deps
    libnss3 libnspr4 \
    libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    libatspi2.0-0 libwayland-client0 \
    fonts-liberation fonts-noto-color-emoji \
    # Virtual display for --headless=new mode (no physical screen)
    xvfb \
    # Process supervision & signal forwarding
    tini \
    # Useful for healthcheck
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Copy installed Python packages from builder ───────────────────
COPY --from=builder /install /usr/local

# ── Install Playwright browser (Chromium only) ────────────────────
RUN playwright install chromium \
 && playwright install-deps chromium

# ── Create non-root user ──────────────────────────────────────────
RUN groupadd --gid 1001 appgroup \
 && useradd --uid 1001 --gid 1001 --no-create-home --shell /bin/bash appuser

# ── Pre-create the X11 socket directory (world-writable, sticky) ──
# Xvfb (running as non-root appuser) needs to create its Unix socket
# inside /tmp/.X11-unix. Without this the directory doesn't exist and
# Xvfb silently skips socket creation → Chromium --headless=new crashes
# with SIGTRAP when it tries to connect to DISPLAY=:99.
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

WORKDIR /app

# ── Copy application code ─────────────────────────────────────────
COPY scraper/   scraper/
COPY configs/   configs/
COPY scrape.py pipeline.py track_history.py entrypoint.sh ./

RUN chmod +x entrypoint.sh \
 && mkdir -p data logs \
 && chown -R appuser:appgroup /app

# ── Volumes for persistent data ───────────────────────────────────
VOLUME ["/app/data", "/app/logs"]

# ── Switch to non-root ────────────────────────────────────────────
USER appuser

# ── Healthcheck: pipeline writes a heartbeat file every cycle ─────
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD test -f /app/logs/.heartbeat \
     && [ $(( $(date +%s) - $(stat -c %Y /app/logs/.heartbeat) )) -lt 3600 ] \
     || exit 1

# ── tini as PID 1 → proper signal forwarding + zombie reaping ─────
ENTRYPOINT ["tini", "--", "/app/entrypoint.sh"]
CMD ["python", "pipeline.py", "run"]
