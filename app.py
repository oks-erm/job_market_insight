from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from celery import Celery
import requests
import secrets
import traceback
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError
import plots
from scraper import linkedin_scraper
from db import get_job_data, create_table
from geoid import country_dict
from skills import tech_jobs
from schedule import create_beat_schedule, generate_link


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['DEBUG'] = True
socketio = SocketIO(app, 
                    message_queue='redis://localhost:6379/0', 
                    async_mode='threading', 
                    engineio_logger=True, 
                    websocket_transports=['websocket', 'xhr-polling'])

celery_app = Celery('celery_app', 
                    broker='redis://localhost:6379/0',
                    backend='redis://localhost:6379/0',
                    broker_connection_retry_on_startup=True,
                    task_serializer='json',  
                    accept_content=['json'],
                    result_serializer='json'
                    )
celery_app.conf.beat_schedule = create_beat_schedule(tech_jobs, country_dict)
celery_app.conf.timezone = 'UTC'
celery_app.autodiscover_tasks(['app'])

CORS(app)
create_table()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get-available-data')
def get_available_data():
    return {
        "available_jobs": tech_jobs,
        "available_locations": [item.title() for item in list(country_dict.keys())]
    }


@celery_app.task(name='app.scrape_linkedin_data')
@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(1))
def scrape_linkedin_data(url, keywords, location, namespace='batch'):
    print(f"Scraping FROM CELERY APP")
    linkedin_scraper(url, 0, namespace)


@socketio.on('search')
def handle_search_event(data):
    keywords = data.get('keywords')
    location = data.get('location')
    namespace = request.sid
    response = process_search_request(keywords, location, namespace)
    emit('existing_data_plots', response, namespace=namespace)


def process_search_request(keywords, location, namespace):
    # Get existing job data from the database
    job_data = get_job_data(keywords, location)

    if job_data.empty:
        print("No existing data found.")
        return {
            'top_skills_plot': None,
            'top_cities_plot': None,
        }

    print("Data for the request is found.")
    search_dataframe = plots.create_search_dataframe(keywords, location)
    top_skills_plot = plots.create_top_skills_plot(
        search_dataframe, keywords, location)
    top_cities_plot = plots.create_top_cities_plot(
        search_dataframe, max_cities=10, keywords=keywords, location=location)

    return {
        'top_skills_plot': top_skills_plot.to_json() if top_skills_plot is not None else None,
        'top_cities_plot': top_cities_plot.to_json() if top_cities_plot is not None else None,
    }


if __name__ == '__main__':
    socketio.run(app)
