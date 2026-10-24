# Stage 1: base
FROM python:3.11-slim AS base

RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid appuser --shell /bin/bash --create-home appuser

# Stage 2: builder
FROM base AS builder

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER appuser
COPY requirements.txt /tmp/requirements.txt
RUN pip install --user --no-cache-dir -r /tmp/requirements.txt

# Stage 3: runtime
FROM base AS runtime

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /home/appuser/.local /home/appuser/.local
COPY app/ /app/app/

ENV PATH="/home/appuser/.local/bin:$PATH"
ENV PYTHONPATH="/app"

USER appuser
WORKDIR /app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
