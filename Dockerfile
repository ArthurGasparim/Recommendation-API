FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pandas/scikit (if needed)
RUN apt-get update && apt-get install -y gcc libpq-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port defined in your main.py (5000)
EXPOSE 5000

# Run uvicorn directly for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]