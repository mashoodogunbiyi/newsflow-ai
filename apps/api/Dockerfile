FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations

RUN python -m pip install --no-cache-dir --upgrade pip
RUN python -m pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
