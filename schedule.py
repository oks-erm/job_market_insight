from celery import chain
from celery.schedules import crontab
from datetime import timedelta
from geoid import country_dict


def generate_link(keyword, location):
    geoid = country_dict.get(location.lower(), None)
    if geoid is None:
        raise ValueError(f"Geoid not found for {location}")
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={location}&geoId={geoid}&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="
    return url


def create_beat_schedule(positions, countries):
    schedule = {}
    for position in positions:
        for country_name, country_code in countries.items():
            task_name = f'scrape-{position}-in-{country_name}'
            schedule[task_name] = {
                'task': 'app.scrape_linkedin_data',
                'schedule': timedelta(hours=3),
                'args': (position, country_name)
            }
    return schedule
