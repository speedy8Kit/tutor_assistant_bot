FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install poetry==2.2.1


COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false && \
    poetry config installer.max-workers 10

RUN poetry install --no-interaction --no-root

COPY . .

RUN mkdir -p /app/data /app/logs

CMD ["bash"]