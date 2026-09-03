FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=10000

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/

RUN set -e; \
    if [ ! -f /app/core/server.py ]; then \
      FOUND=$(find /app -type f -name server.py 2>/dev/null | head -1); \
      echo "LOOKING FOR server.py: $FOUND"; \
      if [ -n "$FOUND" ]; then \
        COREDIR=$(dirname "$FOUND"); \
        BASE=$(dirname "$COREDIR"); \
        echo "FLATTEN $BASE -> /app"; \
        cp -a "$BASE"/. /app/; \
      fi; \
    fi; \
    mkdir -p /app/data/identity /app/data/memory /app/data/grammar /app/data/library \
      /app/data/mentor /app/data/codex /app/data/user /app/data/uploads \
      /app/data/chat /app/data/long_memory /app/data/coaching; \
    ls -la /app; \
    ls -la /app/core | head -15; \
    test -f /app/core/server.py; \
    test -f /app/web/index.html; \
    if [ ! -f /app/wsgi.py ]; then \
      printf 'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nfrom core.server import app\n' > /app/wsgi.py; \
    fi

EXPOSE 10000
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 --chdir /app wsgi:app
