from flask import Flask, render_template, request, jsonify
from flask import Flask, render_template, request
from scraper import linkedin_scraper
from db import get_job_data


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search():
    keywords = request.args.get('keywords')
    location = request.args.get('location')
    # Get existing job data from the database
    job_data = get_job_data()  

    if keywords and location:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId=100364837&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="
        linkedin_scraper(url, 0)

        # Update the job data after scraping
        job_data = get_job_data()

    return jsonify(job_data)


if __name__ == '__main__':
    app.run()
