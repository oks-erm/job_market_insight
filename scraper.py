import requests
import time
import re
import traceback
from bs4 import BeautifulSoup
from skills import tech_skills
from db import create_table, insert_job_data, is_visited_link


RETRY_TIMEOUT = 5
MAX_RETRIES = 5


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
    while retry_count < MAX_RETRIES:
        try:
            response = requests.get(job_link)
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
            if response.status_code == 429 or response.status_code == 503:
                print(f"{response.status_code} Error. Retrying after timeout...")
                time.sleep(RETRY_TIMEOUT)
                retry_count += 1
                continue

            raise Exception(f"Error occurred while scraping job description: {str(e)}")

        except Exception as e:
            raise Exception(f"Unexpected error occurred while scraping job description: {str(e)}")

    print(f"Max retry limit reached for {job_link}. Skipping job description.")
    return [], "N/A"


# Main scraper function
def linkedin_scraper(webpage, page_number):
    print("Scraping function called!!!!!! LINKEDIN_SCRAPER")
    try:
        create_table()
        next_page = webpage + str(page_number)
        response = requests.get(str(next_page))
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
            if page_number < 1000:
                page_number = page_number + 25
                linkedin_scraper(webpage, page_number)
            else:
                print('Scraping completed!')
        else:
            print('No new jobs to scrape. Scraping completed!')
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        raise e
