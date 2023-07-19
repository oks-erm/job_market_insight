from flask import Flask, render_template, request, jsonify
from flask import Flask, render_template, request
from scraper import linkedin_scraper
from db import get_job_data, create_table
import plots
import time
import threading


app = Flask(__name__)
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
        plot_name = f'plot_{keywords}_{location}_{int(time.time())}.png'
        plot_path = f'static/images/{plot_name}'
        plots.create_top_skills_plot(search_dataframe, plot_path)


@app.route('/search', methods=['GET'])
def search():
    keywords = request.args.get('keywords')
    location = request.args.get('location')

    # Get existing job data from the database
    job_data = get_job_data()

    if not job_data.empty:
        # If there is existing data, create search_dataframe using it
        search_dataframe = plots.create_search_dataframe(keywords, location)
        plot_name = f'plot_{keywords}_{location}_{int(time.time())}.png'
        plot_path = f'static/images/{plot_name}'
        plots.create_top_skills_plot(search_dataframe, plot_path)

    if keywords and location:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId=100364837&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="

        # Start the scraping process in the background
        threading.Thread(target=scrape_and_update_data, args=(url, keywords, location)).start()

    return jsonify(plot_path=plot_path)


if __name__ == '__main__':
    app.run()
