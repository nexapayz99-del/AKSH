FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Create sessions directory
RUN mkdir -p /app/sessions

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Run bot
CMD ["python", "main.py"]