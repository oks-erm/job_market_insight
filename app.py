from flask import Flask, json
import csv
from scraper import linkedin_scraper, scrape_job_description


app = Flask(__name__)


@app.route('/')
def index():
    # keywords = request.args.get('keywords')
    # location = request.args.get('location')
    keywords = 'python'
    location = 'Portugal'

    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&geoId=100364837&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="
    linkedin_scraper(url, 0)
    data = []
    with open('linkedin-jobs.csv', 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            data.append(row)

    return json.dumps(data)
