from flask import Flask, render_template, request, jsonify
from flask import Flask, render_template, request
from scraper import linkedin_scraper
from db import get_job_data
import plots
import threading


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search():
    keywords = request.args.get('keywords')
    location = request.args.get('location')

    # Call the create_search_dataframe function from plots.py to get the DataFrame
    search_dataframe = plots.create_search_dataframe(keywords, location)
    plot_path = 'static/images/plot.png'
    plots.create_top_skills_plot(search_dataframe, plot_path)

    # Get existing job data from the database
    job_data = get_job_data()  

    if keywords and location:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId=100364837&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="
        linkedin_scraper(url, 0)

        # Update the job data after scraping
        job_data = get_job_data()

    return jsonify({'plot_path': plot_path, 'job_data': job_data})


if __name__ == '__main__':
    app.run()
