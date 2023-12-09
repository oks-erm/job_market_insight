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
RUN pip install gunicorn==19.1.1 gevent gevent-websocket

# Run gunicorn when the container launches
EXPOSE 8000

CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "4", "application:application", "--worker-connections", "1000", "--access-logfile", "-", "--error-logfile", "-"]
