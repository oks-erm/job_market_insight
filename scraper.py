import requests
import time
import re
import random
import traceback
from fuzzywuzzy import process
from bs4 import BeautifulSoup
from skills import tech_skills, tech_jobs
from db import create_table, insert_job_data, is_visited_link
from proxies import get_request_headers, RETRY_TIMEOUT, MAX_RETRIES, fetch_and_verify_proxies, is_proxy_refresh_needed, get_verified_proxies, store_verified_proxies


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
        verified_proxies = get_verified_proxies()
        if not verified_proxies:
            print("Fetching new proxies...")
            verified_proxies = fetch_and_verify_proxies()
            store_verified_proxies(verified_proxies)
            if not verified_proxies:
                print("No verified proxies available after refreshing.")
                break

        proxy = random.choice(verified_proxies)

        try:
            response = requests.get(job_link, headers=get_request_headers(), proxies={
                                    'http': proxy, 'https': proxy})
            response.raise_for_status()

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

        except (requests.exceptions.ProxyError, requests.exceptions.SSLError):
            print("Proxy error encountered. Switching proxy.")
            verified_proxies.remove(proxy) 
            retry_count += 1
            continue

        except requests.HTTPError as e:
            if response.status_code == 451:
                print("HTTP 451 Error: Access Blocked for Legal Reasons")
                break
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
def linkedin_scraper(webpage, max_pages=100):
    print("Scraping function is called!!! Yo, I'm LINKEDIN_SCRAPER")
    create_table()
    start = 0

    while start < max_pages:
        next_page = webpage + str(start)

        if is_proxy_refresh_needed():
            new_verified_proxies = fetch_and_verify_proxies()
            store_verified_proxies(new_verified_proxies + get_verified_proxies())

        verified_proxies = get_verified_proxies()
        if not verified_proxies:
            print("No verified proxies available.")
            break

        proxy = random.choice(verified_proxies)

        try:
            response = requests.get(next_page, headers=get_request_headers(), proxies={
                                    'http': proxy, 'https': proxy})
            response.raise_for_status()
            print("Status Code:", response.status_code)
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
                    match = process.extractOne(job_title, tech_jobs)
                    if match and match[1] >= 70:
                        unified_title = match[0]
                    else:
                        unified_title = job_title

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
                        'title': unified_title,
                        'category': industries,
                        'company': job_company,
                        'location': job_location,
                        'date': job_date,
                        'skills': ','.join(job_description),
                        'link': job_link
                    })

                    # Log the title and region of the inserted job
                    print(f"Inserted job: '{unified_title}' in '{job_location}'")

                    time.sleep(2)
                except Exception as e:
                    # Log the error and continue with the next job link
                    print(
                        f"An error occurred during scraping job description: {str(e)}")
                    print(traceback.format_exc())

        except (requests.exceptions.ProxyError, requests.exceptions.SSLError):
            print("Proxy error encountered. Switching proxy.")
            verified_proxies.remove(proxy)
            continue

        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            traceback.print_exc()
            break

        start += 1
        print(f'Scraped {job_count} jobs from the page!')
        time.sleep(2)



