FROM python:3.11-slim

WORKDIR /app

# Install system dependencies FIRST
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt BEFORE trying to use it
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]