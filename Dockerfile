FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml .
COPY backend ./backend
COPY cli ./cli

RUN pip install --no-cache-dir .


FROM python:3.12-slim AS runtime

RUN useradd --create-home appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app .

USER appuser

ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]