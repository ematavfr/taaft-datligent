FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (none for psycopg2-binary usually, but good practice)
# RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY updater.py .

CMD ["python", "-u", "updater.py"]
