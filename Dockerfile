# Stage 1: Збірка залежностей у віртуальне середовище
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# Stage 2: Мінімальний hardened рантайм
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"

# Створення не-привілейованого користувача appuser (UID 1000)
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -d /app_code -s /usr/sbin/nologin appuser

WORKDIR /app_code

# Копіювання готового venv із builder
COPY --from=builder /opt/venv /opt/venv

# Копіювання коду проєкту (файли належать root -> appuser має право лише на читання)
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

# Створення директорії для SQLite-бази із правами запису для appuser
RUN mkdir -p /app_code/data && chown appuser:appuser /app_code/data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

# Запуск без --reload, прокси-заголовки від Nginx для правильного визначення IP клієнта
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
