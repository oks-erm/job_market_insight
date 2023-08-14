import psycopg2
import os
from datetime import datetime
from urllib import parse
import pandas as pd
from tenacity import retry, wait_fixed, stop_after_attempt
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
            skills VARCHAR(500),
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    conn.commit()
    cur.close()
    conn.close()


# Helper function to truncate a string
def truncate_string(string, length):
    return string[:length] if len(string) > length else string


# Helper function to insert data into a table
def insert_into_table(cur, table_name, column_name, data_value):
    try:
        cur.execute(
            f'SELECT id FROM {table_name} WHERE {column_name} = %s', (data_value,))
        row = cur.fetchone()

        # Insert data if it doesn't exist
        if not row:
            # Truncate the data_value to fit within the maximum length
            data_value_truncated = data_value[:255]
            cur.execute(
                f'INSERT INTO {table_name} ({column_name}) VALUES (%s) RETURNING id', (data_value_truncated,))
            data_id = cur.fetchone()[0]
        else:
            data_id = row[0]

        return data_id

    except psycopg2.IntegrityError:
        print(f"Something wrong with {table_name} {data_value}.")
        return None
    except psycopg2.errors.StringDataRightTruncation:
        print(f"Truncating {column_name} to fit within the maximum length.")
        data_value_truncated = data_value[:255]
        cur.execute(
            f'INSERT INTO {table_name} ({column_name}) VALUES (%s) RETURNING id', (data_value_truncated,))
        data_id = cur.fetchone()[0]

        return data_id
    

# Insert job data
def insert_job_data(job_data):
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                            database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()

    location_id = insert_into_table(
        cur, 'locations', 'location_name', job_data['location'])
    category_id = insert_into_table(
        cur, 'job_categories', 'category_name', job_data['category'])

    if location_id is None or category_id is None:
        print(f"Failed to insert data into locations or job_categories. Skipping job insertion.")
        cur.close()
        conn.close()
        return None

    try:
        # Truncate the strings to fit within the 255-character limit
        job_data['title'] = truncate_string(job_data['title'], 255)
        job_data['company'] = truncate_string(job_data['company'], 255)
        job_data['skills'] = truncate_string(job_data['skills'], 255)

        current_time = datetime.now()
        
        cur.execute(
            'INSERT INTO jobs (job_id, title, company, location_id, category_id, date, skills, link, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING job_id',
            (job_data['job_id'], job_data['title'], job_data['company'], location_id, category_id, job_data['date'], job_data['skills'], job_data['link'], current_time))
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


# Check visited job_ids in visited table
def is_visited_link(job_id):
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                            database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()

    cur.execute('SELECT job_id FROM visited WHERE job_id = %s', (job_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_job_data(keywords=None, location=None):
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cur = conn.cursor()

        # Prepare the SQL query
        query = '''
            SELECT j.job_id, j.title, j.company, l.location_name as location, c.category_name as category, j.date, j.skills, j.link
            FROM jobs j
            JOIN locations l ON j.location_id = l.id
            JOIN job_categories c ON j.category_id = c.id
        '''

        # Check if keywords and/or location are provided to add filtering conditions to the query
        if keywords and location:
            query += f"WHERE j.title ILIKE '%{keywords}%' AND l.location_name ILIKE '%{location}%'"
        elif keywords:
            query += f"WHERE j.title ILIKE '%{keywords}%'"
        elif location:
            query += f"WHERE l.location_name ILIKE '%{location}%'"

        cur.execute(query)

        job_data = cur.fetchall()

        cur.close()
        conn.close()

        # Convert the fetched data to a DataFrame
        columns = ["job_id", "title", "company", "location",
                "category", "date", "skills", "link"]
        df = pd.DataFrame(job_data, columns=columns)

        return df
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None
