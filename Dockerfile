FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080 \
    RSRSSR_DB_PATH=/tmp/rsrssr/rss_feeds.db

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "server:app"]
