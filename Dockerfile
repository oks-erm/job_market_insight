FROM python:3.9-slim

# Set the working directory
WORKDIR /usr/src/app

# Install requirements.txt
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

RUN pip install gunicorn geventwebsocket

EXPOSE 8000

CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "application:application"]