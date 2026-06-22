# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first (for faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . .

# Expose the Flask port
EXPOSE 5000

# Run the web application
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "5000"]
