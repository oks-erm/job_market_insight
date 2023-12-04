from random import shuffle
from datetime import timedelta
from itertools import product
from geoid import country_dict


def generate_link(keyword, location):
    geoid = country_dict.get(location.lower(), None)
    if geoid is None:
        raise ValueError(f"Geoid not found for {location}")
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={location}&geoId={geoid}&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0&start="
    return url


def create_beat_schedule(positions, countries):
    tasks = []
    for position, (country_name, country_code) in product(positions, countries.items()):
        task_name = f'scrape-{position}-in-{country_name}'
        task_info = {
            'task': 'application.scrape_linkedin_data',
            'schedule': timedelta(hours=5),
            'args': (position, country_name)
        }
        tasks.append((task_name, task_info))

    # Shuffle the list of tasks
    shuffle(tasks)
    schedule = dict(tasks)

    return schedule
