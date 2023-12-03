FROM python:3.9-slim

# Set the working directory
WORKDIR /usr/src/app

# Install requirements.txt
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

RUN pip install gunicorn
EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:application", "--workers=3", "--threads=3"]
