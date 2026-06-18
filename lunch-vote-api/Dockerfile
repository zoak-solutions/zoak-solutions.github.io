FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY server.py manage_tokens.py /app/

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
  && mkdir -p /data \
  && chown -R appuser:appuser /data /app

USER appuser

EXPOSE 8080

CMD ["python", "/app/server.py"]
