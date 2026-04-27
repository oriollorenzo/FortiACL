FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates

RUN python -m compileall -b /app/app \
    && find /app/app -type d -name "__pycache__" -prune -exec rm -rf {} + \
    && find /app/app -type f -name "*.py" ! -name "__init__.py" -delete

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
