# IT Job Market Analysis tool

[LIVE VERSION HERE](http://itjinsights-env.eba-6cv9ca2d.eu-central-1.elasticbeanstalk.com/)

## What's the point?:

 **IT Jobs Insights** is a Flask-based web application designed to provide real-time insights into the trends of IT job market. Built on websocket and Celery for distributed task processing. The application is configured to scrape job data from major job boards and present analytical visualizations to the user. Only open positions are scraped and the data is consistently updated every 24 hours to ensure that the user is presented with the most recent job market trends.

____
![IT Jobs Insights](/static/images/work008.png)

____

## Features:

- Real-Time Data Processing: Flask-SocketIO for handling real-time search requests and emitting job market data to clients.

- Distributed Task Queue: Employs Celery with Redis as the message broker and result backend for handling asynchronous tasks like scraping job data.

- Jupiter Notebooks: for data analysis.

- Data Visualization: Offers dynamic data visualizations including top skills, city and country distributions, and job market trends based on user queries.

_____
## How to run the application:

Set environment variables for Redis URL, email configuration, and other necessary settings.

* Run `python application.py` to start the application server.

* Run `celery -A application.celery worker --loglevel=info` to start the Celery worker.

* Run `celery -A application.celery beat --loglevel=info` to start the Celery scheduler.
_____

## Dependencies

- Flask
- Flask-SocketIO
- Celery
- Redis
- Jupiter Notebooks
- Data Visualization Libraries (Plotly, Matplotlib, Seaborn)

____________________


**Let me know if you managed to brake it!**

