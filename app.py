from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from scraper import linkedin_scraper
from db import get_job_data, create_table
import plots
import threading
import secrets
from queue import Queue


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
socketio = SocketIO(app, async_mode='threading', engineio_logger=True, websocket_transports=['websocket', 'xhr-polling'])
# Allow CORS for all routes
CORS(app)

create_table()

@app.route('/')
def index():
    return render_template('index.html')


def scrape_and_update_data(url, keywords, location):
    # Run scraping to get the newest data
    linkedin_scraper(url, 0)

    # Update the job data after scraping
    job_data = get_job_data()

    if not job_data.empty:
        # If there is existing data (after scraping), create search_dataframe using the updated job data
        search_dataframe = plots.create_search_dataframe(keywords, location)
        new_plot = plots.create_top_skills_plot(search_dataframe, keywords, location)
        print("New plot created")
        # Emit the new plot to all connected clients through the WebSocket
        socketio.emit('update_plot', {'plot_json': new_plot.to_json()})


def process_search_request(keywords, location):
    # Get existing job data from the database
    job_data = get_job_data()

    # Check if there is existing data to create Plotly figure
    if not job_data.empty:
        search_dataframe = plots.create_search_dataframe(keywords, location)
        plot = plots.create_top_skills_plot(search_dataframe, keywords, location)
    else:
        search_dataframe = None
        plot = None

    if keywords and location:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId=100364837&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="

        # Start the scraping process in the background
        threading.Thread(target=scrape_and_update_data,
                         args=(url, keywords, location)).start()

    return {'plot_json': plot.to_json() if plot else None}


@app.route('/search', methods=['GET'])
def search():
    keywords = request.args.get('keywords')
    location = request.args.get('location')

    return process_search_request(keywords, location)


@socketio.on('search')
def handle_search_event(data):
    keywords = data.get('keywords')
    location = data.get('location')

    response = process_search_request(keywords, location)

    # Emit the response to the current client through the WebSocket
    emit('update_plot', response)


if __name__ == '__main__':
    socketio.run(app)
