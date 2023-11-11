import requests
import time
import re
import traceback
import random
from bs4 import BeautifulSoup
from skills import tech_skills
from db import create_table, insert_job_data, is_visited_link


RETRY_TIMEOUT = 5
MAX_RETRIES = 5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/90.0.4430.78 Mobile/14E5239e Safari/602.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/90.0.818.56",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko"
]


def fetch_proxies(url='https://www.sslproxies.org/'):
    proxies = []
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    rows = table.tbody.find_all('tr')
    for row in rows:
        ip = row.find_all('td')[0].text
        port = row.find_all('td')[1].text
        proxies.append(f'http://{ip}:{port}')
    return proxies


PROXIES = fetch_proxies()


def get_request_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS)
    }


def get_proxy():
    return random.choice(PROXIES)


# filter skills from job description
def filter_skills(description):
    filtered_skills = []
    for skill in tech_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', description, flags=re.IGNORECASE):
            filtered_skills.append(skill)
    return filtered_skills


# get job id from job link
def get_job_id(job_link):
    job_id = re.search(r"-(\d+)\?", job_link)
    if job_id:
        return job_id.group(1)
    return None


# scrape job description and industry visiting job link
def scrape_job_description(job_link):
    retry_count = 0
    timeout = RETRY_TIMEOUT
    while retry_count < MAX_RETRIES:
        try:
            response = requests.get(job_link, headers=get_request_headers(), proxies={'http': get_proxy()})
            response.raise_for_status()
            print(response.status_code)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # get job description
                job_description = soup.find(
                    'div', class_='description__text').text.strip() if soup.find('div', class_='description__text') else 'N/A'
                req_skills = filter_skills(job_description)

                # get industries
                criteria_list = soup.find('ul', class_='description__job-criteria-list')
                fourth_child = criteria_list.select('li:nth-child(4)')
                if fourth_child:
                    industries_element = fourth_child[0].find(
                        'span', class_='description__job-criteria-text')
                    if industries_element:
                        industries = industries_element.text.strip()
                    else:
                        industries = 'N/A'
                        print('Industries not found')
                else:
                    industries = 'N/A'
                    print('4th child item not found')
                return list(set(req_skills)), industries

        except requests.HTTPError as e:
            if response.status_code in [429, 503]:
                print(
                    f"{response.status_code} Error. Retrying after {timeout} seconds...")
                time.sleep(timeout)
                timeout *= 2  # exponential backoff
                retry_count += 1
                continue
            else:
                raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            traceback.print_exc()
            break

    if retry_count >= MAX_RETRIES:
        print(
            f"Max retry limit reached for {job_link}. Skipping job description.")
    return [], "N/A"


# Main scraper function
def linkedin_scraper(webpage, max_pages=1000):
    print("Scraping function called!!!!!! LINKEDIN_SCRAPER")
    create_table()
    while page_number < max_pages:
        next_page = webpage + str(page_number)
        try:
            response = requests.get(next_page, headers=get_request_headers(), proxies={
                                    'http': get_proxy()})
            soup = BeautifulSoup(response.content, 'html.parser')

            jobs = soup.find_all(
                'div', class_='base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card')

            job_count = 0  # Track the number of new jobs scraped in this iteration

            for job in jobs:
                try:
                    job_link = job.find('a', class_='base-card__full-link')['href']
                    job_id = get_job_id(job_link)

                    if is_visited_link(job_id):
                        print(f"Skipping duplicate job")
                        continue

                    job_title = job.find(
                        'h3', class_='base-search-card__title').text.strip()
                    job_company = job.find(
                        'h4', class_='base-search-card__subtitle').text.strip()
                    job_location = job.find(
                        'span', class_='job-search-card__location').text.strip()
                    job_date_field = job.find(
                        'time', class_=['job-search-card__listdate', 'job-search-card__listdate--new'])['datetime']
                    if job_date_field is not None:
                        job_date = job_date_field
                    else:
                        job_date = "N/A"

                    job_description, industries = scrape_job_description(job_link)
                    if job_description is not []:
                        job_count += 1

                    # Insert job data
                    insert_job_data({
                        'job_id': job_id,
                        'title': job_title,
                        'category': industries,
                        'company': job_company,
                        'location': job_location,
                        'date': job_date,
                        'skills': ','.join(job_description),
                        'link': job_link
                    })

                    time.sleep(2)
                except Exception as e:
                    # Log the error and continue with the next job link
                    print(
                        f"An error occurred during scraping job description: {str(e)}")
                    print(traceback.format_exc())

            print(f'Scraped {job_count} jobs from the page!')

            if job_count > 0:
                page_number += 25
            else:
                print('No new jobs to scrape. Scraping completed!')
                break
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            traceback.print_exc()
            break
        time.sleep(2)
