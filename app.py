from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from celery import Celery
import requests
import json
import secrets
import traceback
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError
import plots
from scraper import linkedin_scraper
from db import get_job_data, create_table


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
socketio = SocketIO(app, message_queue='redis://localhost:6379/0', async_mode='threading', engineio_logger=True, websocket_transports=['websocket', 'xhr-polling'])
celery_app = Celery('celery_app', 
                    broker='redis://localhost:6379/0',
                    backend='redis://localhost:6379/0',
                    broker_connection_retry_on_startup=True,
                    task_serializer='json',  
                    # Accept 'json' content from tasks
                    accept_content=['json'],
                    result_serializer='json'
                    )

CORS(app)
create_table()


@app.route('/')
def index():
    return render_template('index.html')


@celery_app.task(name='app.scrape_linkedin_data')
@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(1))
def scrape_linkedin_data(url, keywords, location, namespace):
    print(f"Scraping FROM CELERY APP")
    try:
        # Set a custom User-Agent header to mimic a real web browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

        linkedin_scraper(url, 0, namespace, headers=headers)

        print("AFTER LINKEDIN SCRAPER")
        # Scraping is complete, update the job data after scraping
        job_data = get_job_data(keywords, location)
        print(f'job_data {job_data}')

        if not job_data.empty:
            # If there is existing data (after scraping)
            new_search_dataframe = plots.create_search_dataframe(
                keywords, location)
            new_top_skills_plot = plots.create_top_skills_plot(
                new_search_dataframe, keywords, location)
            new_top_cities_plot = plots.create_top_cities_plot(
                new_search_dataframe, max_cities=10, keywords=keywords, location=location)

            data = {
                'new_top_skills_json': new_top_skills_plot.to_json(),
                'new_top_cities_json': new_top_cities_plot.to_json(),
                namespace: namespace
            }

            socketio.emit('update_plot', data)
        else:
            results = {
                'message': 'Fetching data, please wait...',
                'namespace': namespace
            }
            socketio.emit('no_data', results)

    except requests.exceptions.HTTPError as e:
        print(f"Error occurred while scraping job description: {str(e)}")
        print(traceback.format_exc())
        raise e
    except RetryError as e:
        print("RetryError occurred. The task will not be retried further.")
        print(traceback.format_exc())
    except Exception as e:
        print(f"Unexpected error occurred while scraping job description: {str(e)}")
        print(traceback.format_exc())


@socketio.on('search')
def handle_search_event(data):
    keywords = data.get('keywords')
    location = data.get('location')
    namespace = request.sid
    response = process_search_request(keywords, location, namespace)

    emit('existing_data_plots', response)


def process_search_request(keywords, location, namespace):
    socketio.emit('show_progress_bar', namespace=namespace)

    # Get existing job data from the database
    job_data = get_job_data(keywords, location)

    # Check if there is existing data to create Plotly figures
    if not job_data.empty:
        print("Existing data found.")

        search_dataframe = plots.create_search_dataframe(keywords, location)
        top_skills_plot = plots.create_top_skills_plot(
            search_dataframe, keywords, location)
        top_cities_plot = plots.create_top_cities_plot(
            search_dataframe, max_cities=10, keywords=keywords, location=location)

    else:
        print("No existing data found.")
        top_skills_plot = None
        top_cities_plot = None

    if keywords and location:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId=104738515&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="

        scrape_linkedin_data.apply_async(
            args=[url, keywords, location, namespace],
            task_id=f'{keywords}_{location}'
        )
    #existing data
    return {
        'top_skills_plot': top_skills_plot.to_json() if top_skills_plot is not None else None,
        'top_cities_plot': top_cities_plot.to_json() if top_cities_plot is not None else None,
    }


@socketio.on('show_progress_bar')
def show_progress_bar():
    emit('show_progress_bar')


@socketio.on_error()  
def handle_socketio_error(e):
    print(f"WebSocket error occurred: {e}")
    print(traceback.format_exc())

celery_app.autodiscover_tasks(['app'])


if __name__ == '__main__':
    socketio.run(app)
