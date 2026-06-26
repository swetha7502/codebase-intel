FROM python:3.10-slim

WORKDIR /app

# System deps for psycopg2, gitpython, tree-sitter
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command runs the API server.
# Override with "celery -A app.core.celery_app worker --loglevel=info --concurrency=1"
# for the worker container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
