FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .
COPY .env .

# Create sessions directory
RUN mkdir -p /app/sessions

# Run bot
CMD ["python", "-u", "main.py"]