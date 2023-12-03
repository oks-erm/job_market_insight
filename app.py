import requests
import secrets
import traceback
import plots
import re
import os
from flask_mail import Mail, Message
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from celery import Celery
from markupsafe import escape
from scraper import linkedin_scraper
from db import get_job_data, create_table
from geoid import country_dict
from skills import tech_jobs
from celery.exceptions import MaxRetriesExceededError
from schedule import create_beat_schedule, generate_link
if os.path.exists('env.py'):
    import env  # noqa # pylint: disable=unused-import


application = Flask(__name__)
application.config['SECRET_KEY'] = secrets.token_hex(32)
application.config['DEBUG'] = False

application.config['MAIL_SERVER'] = os.environ.get('EMAIL_HOST')
application.config['MAIL_PORT'] = os.environ.get('EMAIL_PORT')
application.config['MAIL_USERNAME'] = os.environ.get('EMAIL_HOST_USER')
application.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_HOST_PASSWORD')

# websocket
socketio = SocketIO(application,
                    message_queue='redis://localhost:6379/0', 
                    async_mode='threading', 
                    engineio_logger=True, 
                    websocket_transports=['websocket', 'xhr-polling'])

# celery
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

CORS(application)
mail = Mail(application)
create_table()


@application.route('/')
def index():
    return render_template('index.html')


@application.route('/get-available-data')
def get_available_data():
    return {
        "available_jobs": tech_jobs,
        "available_locations": [item.title() for item in list(country_dict.keys())]
    }


@application.route('/process-contact-form', methods=['POST'])
def process_contact_form():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()

    # Validate data
    if not name or not email or not message:
        return jsonify({'error': 'All fields are required.'}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'error': 'Invalid email address.'}), 400
    if not message or len(message) > 500:
        return jsonify({'error': 'Invalid message.'}), 400
    
    # Send email
    send_email(
        subject='ITJM insight app Contact Form',
        sender=application.config.get('MAIL_USERNAME'),
        recipients=[application.config.get('MAIL_USERNAME')],
        text_body=f"Name: {sanitize_input(name)}\nEmail: {sanitize_input(email)}\nMessage: {sanitize_input(message)}"
    )

    return jsonify({'message': 'Your message has been sent successfully!'})


def sanitize_input(input_string):
    return escape(input_string)


def send_email(subject, sender, recipients, text_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    mail.send(msg)


@celery_app.task(bind=True, name='app.scrape_linkedin_data', max_retries=3)
def scrape_linkedin_data(self, position, country_name, *args, **kwargs):
    print(f"Scraping FROM CELERY APP for {position} in {country_name}")
    url = generate_link(position, country_name)

    try:
        linkedin_scraper(url)
    except requests.exceptions.HTTPError as e:
        print(f"Error occurred while scraping job description: {str(e)}")
        print(traceback.format_exc())
        raise e
    except Exception as e:
        print(
            f"Unexpected error occurred while scraping job description: {str(e)}")
        print(traceback.format_exc())
        try:
            self.retry(exc=e, countdown=30)
        except MaxRetriesExceededError:
            print("Max retries exceeded for scraping task.")


@socketio.on('search')
def handle_search_event(data):
    keywords = data.get('keywords')
    location = data.get('location')
    response = process_search_request(keywords, location)
    emit('existing_data_plots', response)


def process_search_request(keywords, location):
    # Get existing job data from the database
    job_data = get_job_data(keywords, location)

    if job_data.empty:
        print("No existing data found.")
        return {
            'top_skills_plot': None,
            'top_cities_plot': None,
            'jobs_distribution_plot': None,
        }

    print("Data for the request is found.")

    top_skills_plot = plots.create_top_skills_plot(
        job_data, keywords, location)
    top_cities_plot = plots.create_top_cities_plot(
        job_data, max_cities=10, keywords=keywords, location=location)
    jobs_distribution_plot = plots.create_job_distribution_plot(
        keywords, location)

    return {
        'top_skills_plot': top_skills_plot.to_json() if top_skills_plot is not None else None,
        'top_cities_plot': top_cities_plot.to_json() if top_cities_plot is not None else None,
        'jobs_distribution_plot': jobs_distribution_plot.to_json() if jobs_distribution_plot is not None else None,
    }


celery_app.autodiscover_tasks(['app'])


if __name__ == '__main__':
    socketio.run(application, port=8000)
