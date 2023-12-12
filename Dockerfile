FROM python:3.9-slim

# Set the working directory
WORKDIR /usr/src/app

# Install requirements.txt
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

RUN pip install gunicorn gevent==21.8.0 gevent-websocket

RUN adduser -D user
USER user

EXPOSE 8080

CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "application:application"]