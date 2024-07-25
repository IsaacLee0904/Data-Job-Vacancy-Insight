FROM python:3.8-slim-buster

# Set the working directory to /app inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install system packages and Python dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    tzdata \
    git && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the time zone
RUN ln -fs /usr/share/zoneinfo/Asia/Taipei /etc/localtime && dpkg-reconfigure -f noninteractive tzdata

# Copy the current directory contents into the container at /app
COPY . .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define an environment variable
ENV NAME JobVacancyInsight

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:9100", "src.dashboard_src.dashboard_index:server"]