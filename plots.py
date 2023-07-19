import matplotlib
matplotlib.use('Agg')

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from geotext import GeoText
import psycopg2
from urllib import parse
import os
if os.path.exists('env.py'):
    import env  # noqa # pylint: disable=unused-import


def create_search_dataframe(keywords, location):
    # Connect to the database
    DATABASE_URL = os.environ['DATABASE_URL']
    parse.uses_netloc.append('postgres')
    url = parse.urlparse(DATABASE_URL)
    DB_HOST = url.hostname
    DB_PORT = url.port
    DB_NAME = url.path[1:]
    DB_USER = url.username
    DB_PASSWORD = url.password

    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                            database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

    cur = conn.cursor()

    query = f'''
        SELECT j.job_id, j.title, j.company, l.location_name as location, c.category_name as category, j.date, j.skills, j.link
        FROM jobs j
        JOIN locations l ON j.location_id = l.id
        JOIN job_categories c ON j.category_id = c.id
        WHERE (j.title ILIKE '%{keywords}%' OR j.company ILIKE '%{keywords}%' OR j.skills ILIKE '%{keywords}%')
        AND l.location_name ILIKE '%{location}%'
    '''
    cur.execute(query)
    job_data = cur.fetchall()

    cur.close()
    conn.close()

    # Create pandas DataFrame
    df = pd.DataFrame(job_data, columns=[
                      "job_id", "title", "company", "location", "category", "date", "skills", "link"])

    # Fill missing values with "N/A"
    df_filled = df.fillna(value="N/A")


    # Extract city and country names from the 'location' column
    def extract_place_names(location_str):
        places = GeoText(location_str)
        city = places.cities[0] if places.cities else ''
        country = places.countries[0] if places.countries else ''
        return city, country

    df_filled[['city', 'country']] = df_filled['location'].apply(
        lambda x: pd.Series(extract_place_names(x)))

    # Sort the DataFrame by the 'date' column in descending order
    df_sorted = df_filled.sort_values('date', ascending=False)

    # Return the DataFrame for the search query
    return df_sorted


def create_top_skills_plot(search_dataframe, output_filename):
    # Perform necessary plotting using the search_dataframe
    max_skills = 20
    top_skills_df = get_top_skills(search_dataframe, max_skills)

    # Create the horizontal bar chart
    plt.figure(figsize=(10, max_skills/2))
    sns.barplot(x='frequency', y='skill',
                data=top_skills_df, palette='viridis')
    for index, value in enumerate(top_skills_df['frequency']):
        plt.text(value, index, str(value), ha='left', va='center')
    plt.xlabel('Frequency')
    plt.ylabel('Skills')
    plt.title(
        f'Horizontal Bar Chart of Skill Popularity (top {max_skills} skills)')

    # Save the plot as an image file
    plt.savefig(output_filename)

    plt.close()


def get_top_skills(dataframe, max_skills):
    # Split skills and expand the DataFrame
    dataframe['skills'] = dataframe['skills'].str.split(',')
    df_expanded = dataframe.explode('skills')
    df_expanded.head()

    skill_counts = df_expanded['skills'].str.strip().value_counts()
    sorted_skills = skill_counts.sort_values(ascending=False)

    # Create a new DataFrame for all skills and their frequency
    skills_df = pd.DataFrame(
        {'skill': sorted_skills.index, 'frequency': sorted_skills.values})
    skills_df = skills_df[skills_df['skill'].notna() & (
        skills_df['skill'].str.strip() != '')]

    # Filter the skills to display the top ones
    top_skills_df = skills_df.head(max_skills)

    return top_skills_df
