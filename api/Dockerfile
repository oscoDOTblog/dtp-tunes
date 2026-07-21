FROM python:3.12-slim-bookworm AS base

RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg curl \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --system --gid 1001 tunes \
  && useradd --system --uid 1001 --gid tunes --home /app --shell /usr/sbin/nologin tunes

WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY app ./app

RUN mkdir -p /music /cache \
  && chown -R tunes:tunes /app /cache

USER tunes
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MUSIC_PATH=/music \
    CACHE_PATH=/cache

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
