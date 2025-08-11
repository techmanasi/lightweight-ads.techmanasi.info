# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED True
ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port Gunicorn will run on
# The PORT environment variable is automatically set by Cloud Run.
EXPOSE $PORT

# Run the app using a production-grade WSGI server (Gunicorn)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app.main:app
