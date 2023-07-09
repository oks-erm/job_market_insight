import psycopg2
import os
from urllib import parse
from psycopg2 import IntegrityError
if os.path.exists('env.py'):
    import env


DATABASE_URL = os.environ['DATABASE_URL']
# Parse the connection URL
parse.uses_netloc.append('postgres')
url = parse.urlparse(DATABASE_URL)
DB_HOST = url.hostname
DB_PORT = url.port
DB_NAME = url.path[1:]
DB_USER = url.username
DB_PASSWORD = url.password


def create_table():
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                            database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()

    # Create locations table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            location_name VARCHAR(255),
            geo_id VARCHAR(255) UNIQUE
        )
    ''')


    # Create job_categories table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS job_categories (
            id SERIAL PRIMARY KEY,
            category_name VARCHAR(255)
        )
    ''')

    # Create jobs table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            job_id VARCHAR(255) UNIQUE,
            title VARCHAR(255),
            company VARCHAR(255),
            location_id INTEGER REFERENCES locations (id),
            category_id INTEGER REFERENCES job_categories (id),
            date VARCHAR(255),
            skills VARCHAR(255),
            link TEXT
        )
    ''')

    # Create visited table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS visited (
            id SERIAL PRIMARY KEY,
            job_id VARCHAR(255) UNIQUE,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    ''')

    # cur.execute(f"SELECT * FROM visited")
    # rows = cur.fetchall()
    # print(rows)

    # cur.execute(f"SELECT * FROM jobs")
    # rows = cur.fetchall()
    # print(rows)

    conn.commit()
    cur.close()
    conn.close()


# insert job data
def insert_job_data(job_data):
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                            database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()

    try:
        # Get location_id from locations table
        cur.execute('SELECT id FROM locations WHERE location_name = %s',
                    (job_data['location'],))
        location_id_row = cur.fetchone()

        # Insert location if it doesn't exist
        if not location_id_row:
            cur.execute(
                'INSERT INTO locations (location_name) VALUES (%s) RETURNING id', (job_data['location'],))
            location_id = cur.fetchone()[0]
        else:
            location_id = location_id_row[0]

        conn.commit()
    except psycopg2.IntegrityError:
        print(
            f"Something wrong with locations {location_id}.")
        location_id = None

    try:
        # Get category_id from job_categories table
        cur.execute(
            'SELECT id FROM job_categories WHERE category_name = %s', (job_data['category'],))
        category_id_row = cur.fetchone()

        # Insert category if it doesn't exist
        if not category_id_row:
            cur.execute(
                'INSERT INTO job_categories (category_name) VALUES (%s) RETURNING id', (job_data['category'],))
            category_id = cur.fetchone()[0]
        else:
            category_id = category_id_row[0]

        conn.commit()
    except psycopg2.IntegrityError:
        print(
            f"Something wrong with categories {category_id}.")
        category_id = None

    try:
        # Insert job data
        cur.execute(
            'INSERT INTO jobs (job_id, title, company, location_id, category_id, date, skills, link) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING job_id',
            (job_data['job_id'], job_data['title'], job_data['company'], location_id, category_id, job_data['date'], job_data['skills'], job_data['link']))
        job_id = cur.fetchone()[0]

        # Insert job_id into visited table
        cur.execute('INSERT INTO visited (job_id) VALUES (%s)', (job_id,))

        conn.commit()
        print(f"Inserted job_id: {job_id} into jobs and visited table.")
    except psycopg2.IntegrityError:
        print(
            f"Duplicate entry for job data: {job_data}. Skipping job insertion.")
        job_id = None

    cur.close()
    conn.close()

    return job_id


# check visited job_ids in visited table
def is_visited_link(job_id):
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                            database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()

    cur.execute('SELECT job_id FROM visited WHERE job_id = %s', (job_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None


def get_job_data():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT job_id, title, company, location_id, category_id, date, skills, link
        FROM jobs
        '''
    )

    job_data = cur.fetchall()

    cur.close()
    conn.close()

    return job_data
