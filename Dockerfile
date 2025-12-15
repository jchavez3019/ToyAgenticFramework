# python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency files and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the rest of the application code
COPY . /app

# Expose the port (FastAPI port)
EXPOSE 8000

# The entrypoint for the application is handled by docker-compose command