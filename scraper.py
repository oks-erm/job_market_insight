import requests
import time
import csv
import re
from bs4 import BeautifulSoup
from skills import tech_skills


file = open('linkedin-jobs.csv', 'a')
writer = csv.writer(file)
writer.writerow(['Title', 'Company', 'Location', 'Date', 'Skills', 'Link'])


def filter_skills(description):
    filtered_skills = []
    for skill in tech_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', description, flags=re.IGNORECASE):
            filtered_skills.append(skill)
    return filtered_skills


def scrape_job_description(job_link):
    response = requests.get(job_link)
    print(response.status_code)
    soup = BeautifulSoup(response.content, 'html.parser')
    job_description = soup.find(
        'div', class_='description__text').text.strip() if soup.find('div', class_='description__text') else 'N/A'
    print(job_description)
    req_skills = filter_skills(job_description)

    return list(set(req_skills))


def linkedin_scraper(webpage, page_number):
    next_page = webpage + str(page_number)
    print(str(next_page))
    response = requests.get(str(next_page))
    soup = BeautifulSoup(response.content, 'html.parser')

    jobs = soup.find_all(
        'div', class_='base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card')

    for job in jobs:
        job_title = job.find(
            'h3', class_='base-search-card__title').text.strip()
        job_company = job.find(
            'h4', class_='base-search-card__subtitle').text.strip()
        job_location = job.find(
            'span', class_='job-search-card__location').text.strip()
        job_link = job.find('a', class_='base-card__full-link')['href']
        job_date_field = job.find(
            'time', class_=['job-search-card__listdate', 'job-search-card__listdate--new'])['datetime']
        if job_date_field is not None:
            job_date = job_date_field
        else:
            job_date = "N/A"

        job_description = scrape_job_description(job_link)

        writer.writerow([
            job_title,
            job_company,
            job_location,
            job_date,
            job_description,
            job_link,
        ])

        time.sleep(3)

    print('scraped the page successfully!')

    if page_number < 25:
        page_number = page_number + 25
        linkedin_scraper(webpage, page_number)
    else:
        file.close()
        print('File closed')
