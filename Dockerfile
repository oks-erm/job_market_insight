FROM python:3.9-slim

# Set the working directory
WORKDIR /usr/src/app

# Install requirements.txt
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Install Gunicorn and Gevent
RUN pip install gunicorn gevent

# Run gunicorn when the container launches
EXPOSE 8000
