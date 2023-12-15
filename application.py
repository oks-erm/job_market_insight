from gevent import monkey
monkey.patch_all()
import requests
import secrets
import traceback
import plots
import re
import os
import redis
import logging
import json
from flask_mail import Mail, Message
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from celery import Celery
from markupsafe import escape
from scraper import linkedin_scraper
from db import get_job_data, create_table, email_to_db
from custom_logs import CustomSocketIOLogger
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

if application.config['DEBUG']:
    redis_url = 'redis://localhost:6379/0'
else:
    redis_url = os.environ.get('REDIS_URL')

# Redis
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

redis_client.set('test_key', 'Redis is working!')
value = redis_client.get('test_key')
print(value)

# websocket
socketio = SocketIO(application,
                    message_queue=redis_url,
                    async_mode='gevent', 
                    engineio_logger=True, 
                    cors_allowed_origins="*",
                    websocket_transports=['websocket']
                    )

# celery
celery_app = Celery('celery_app', 
                    broker=redis_url,
                    backend=redis_url,
                    broker_connection_retry_on_startup=True,
                    task_serializer='json',  
                    accept_content=['json'],
                    result_serializer='json'
                    )
celery_app.conf.beat_schedule = create_beat_schedule(tech_jobs, country_dict)
celery_app.conf.timezone = 'UTC'

logging.setLoggerClass(CustomSocketIOLogger)
logger = logging.getLogger('socketio')
logger.setLevel(logging.DEBUG)

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
    email_success = send_email(
        subject='ITJM insight app Contact Form',
        sender=application.config.get('MAIL_USERNAME'),
        recipients=[application.config.get('MAIL_USERNAME')],
        text_body=f"Name: {sanitize_input(name)}\nEmail: {sanitize_input(email)}\nMessage: {sanitize_input(message)}"
    )

    if not email_success:
        # Save to database
        email_to_db(name, email, message)
        return jsonify({'error': 'An error occurred while sending your message. Please try again later.'}), 500
    
    return jsonify({'message': 'Your message has been sent successfully!'})


def sanitize_input(input_string):
    return escape(input_string)


def send_email(subject, sender, recipients, text_body):
    try:
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = text_body
        mail.send(msg)
        return True
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return False

# SocketIO events
@celery_app.task(bind=True, name='application.scrape_linkedin_data', max_retries=3)
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

# SocketIO events
@socketio.on('connect')
def handle_connect():
    client_id = request.args.get('client_id')
    short_client_id = client_id[:6] if client_id else None
    print(f"Client {short_client_id} connected")
    if client_id:
        # Check Redis for any stored data
        stored_data = redis_client.get(client_id)
        print('stored_data:', stored_data)
        if stored_data:
            emit('existing_data_plots', json.loads(stored_data.decode('utf-8')))
            redis_client.delete(client_id)  # Clear stored data


@socketio.on('search')
def handle_search_event(data):
    client_id = request.args.get('client_id')
    try:
        keywords = data.get('keywords')
        location = data.get('location')
        response = process_search_request(keywords, location)
        if response is None or response.get('top_skills_plot') is None or response.get('top_cities_plot') is None or response.get('jobs_distribution_plot') is None:
            emit('no_data_found')
            return
        # Store response in Redis
        serialized_response = json.dumps(response)
        print('serialized_response', serialized_response)

        redis_client.set(client_id, serialized_response, ex=300)
        emit('existing_data_plots', response)
    except Exception as e:
        emit('error', {'message': str(e)})
        print(f"Error occurred: {str(e)}")


@socketio.on_error()
def default_error_handler(e):
    emit('server_error', {'error': str(e)})
    print(f"Error occurred: {str(e)}")


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')


def process_search_request(keywords, location):
    # Get existing job data from the database
    job_data = get_job_data(keywords, location)

    if job_data is None:
        print("No existing data found.")
        return {
            'top_skills_plot': None,
            'top_cities_plot': None,
            'jobs_distribution_plot': None,
        }

    print("Data for the request is found.")

    top_skills_plot = plots.create_top_skills_plot(
        job_data, keywords, location)
    print("Top skills plot is created.")

    top_cities_plot = plots.create_top_cities_plot(
        job_data, max_cities=10, keywords=keywords, location=location)
    print("Top cities plot is created.")

    jobs_distribution_plot = plots.create_job_distribution_plot(
        keywords, location)
    print("Jobs distribution plot is created.")
    
    return {
        'top_skills_plot': top_skills_plot.to_json() if top_skills_plot is not None else None,
        'top_cities_plot': top_cities_plot.to_json() if top_cities_plot is not None else None,
        'jobs_distribution_plot': jobs_distribution_plot.to_json() if jobs_distribution_plot is not None else None,
    }


celery_app.autodiscover_tasks(['application'])


if __name__ == '__main__':
    socketio.run(application, host='0.0.0.0', port=8000)
