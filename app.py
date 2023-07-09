from flask import Flask, json
import csv
from scraper import linkedin_scraper
from db import get_job_data


app = Flask(__name__)


@app.route('/')
def index():
    # keywords = request.args.get('keywords')
    # location = request.args.get('location')
    keywords = 'python'
    location = 'Portugal'

    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId=100364837&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="
    linkedin_scraper(url, 0)
    job_data = get_job_data()

    return json.dumps(job_data)
