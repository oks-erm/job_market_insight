FROM python:3.9-slim

# Set the working directory
WORKDIR /usr/src/app

# Install requirements.txt
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Install uwsgi
RUN pip install uwsgi

EXPOSE 8000

CMD ["uwsgi", "--http", "0.0.0.0:8000", "--module", "app:application", "--master", "--processes", "3", "--threads", "2", "--gevent", "1000", "--http-websockets"]