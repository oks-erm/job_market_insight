
import plotly.graph_objects as go
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from geotext import GeoText
import psycopg2
from urllib import parse
import os
from db import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
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
        WHERE (j.title ILIKE '%{keywords}%' AND l.location_name ILIKE '%{location}%')
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

    # Convert 'date' column to datetime
    df_filled['date'] = pd.to_datetime(df['date'])
   
    # Function to extract city and country names from 'location'
    def extract_place_names(location_str):
        places = GeoText(location_str)
        city = places.cities[0] if places.cities else ''
        country = places.countries[0] if places.countries else ''
        return city, country

    df_filled[['city', 'country']] = df_filled['location'].apply(
        lambda x: pd.Series(extract_place_names(x)))

    # Split the 'location' column into 'city' and 'country' columns
    df_filled.drop(columns=['location'], inplace=True)

   # Sort the DataFrame by the 'date' column in descending order
    df_sorted = df_filled.sort_values('date', ascending=False)

    return df_sorted


def create_top_skills_plot(df, keywords=None, location=None, fig=None):
    max_skills = 20
    top_skills_df = get_top_skills(df, max_skills)

    top_skills_df = top_skills_df.sort_values(by='frequency', ascending=True)

    new_fig = px.bar(
        top_skills_df,
        x='frequency',
        y='skill',
        orientation='h',
        color='frequency',
        labels={'frequency': 'Frequency', 'skill': 'Skills'},
        title=f'Top {max_skills} skills for {keywords} jobs in {location}',
        height=600,  
        width=800,  
    )

    # Appearance of the bars
    new_fig.update_traces(
        # Add black outline to the bars
        marker=dict(line=dict(width=1, color='black')),
        showlegend=False, 
    )

    # Adjust the layout
    new_fig.update_layout(
        yaxis=dict(categoryorder='total ascending', showticklabels=True),
        margin=dict(l=50, r=10, t=50, b=10),  # Reduce the margins
        title_x=0.5,  # Center the title along the x-axis
    )

    if fig is not None:
        # Update with the new data
        fig.data = new_fig.data
        fig.layout = new_fig.layout
        return fig

    return new_fig


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


def create_top_cities_plot(df, max_cities, keywords=None, location=None, fig=None):
    # Get the top cities DataFrame
    top_cities_df = get_top_cities(df, max_cities)

    # Create the horizontal bar chart
    fig = px.bar(
        top_cities_df,
        x='job_count',
        y='city',
        orientation='h',
        title=f'Job Distribution by City (Top {top_cities_df.shape[0]} in {location})',
        labels={'job_count': 'Number of Jobs', 'city': 'City'},
        color='job_count',
        color_continuous_scale='Viridis', 
        opacity=0.7,
        height=370,
        width=800
    )

    # Appearance of the bars
    fig.update_traces(
        # Add black outline to the bars
        marker=dict(line=dict(width=1, color='black')),
        showlegend=False,
    )

    # Set the layout for the chart
    fig.update_layout(
        margin=dict(l=50, r=50, t=50, b=20),  
        xaxis_title='Number of Jobs',
        yaxis_title='City',
        title_x=0.5
    )

    return fig


def get_top_cities(df, max_cities):
    # Group the data by 'city' and 'country' and count the number of jobs in each group
    grouped_data = df.groupby(
        ['city', 'country']).size().reset_index(name='job_count')

    # Filter out empty string cities
    grouped_data = grouped_data[grouped_data['city'] != '']

    # Sort the data by job_count in descending order
    sorted_data = grouped_data.sort_values(by='job_count', ascending=False)

    # Get the top cities with the highest job counts
    top_cities = sorted_data.head(max_cities)

    # Sort the DataFrame again to place the most popular job titles on top
    top_cities = top_cities.sort_values(by='job_count', ascending=True)

    return top_cities


def create_job_distribution_plot(search_term, excluded_country):
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()

    query = f'''
        SELECT j.job_id, j.title, l.location_name as location
        FROM jobs j
        JOIN locations l ON j.location_id = l.id
        WHERE j.title ILIKE %s AND l.location_name NOT ILIKE %s
    '''
    cur.execute(query, ('%' + search_term + '%', '%' + excluded_country + '%'))
    job_data = cur.fetchall()
    cur.close()
    conn.close()

    df = pd.DataFrame(job_data, columns=["job_id", "title", "location"])

    df['country'] = df['location'].apply(lambda x: x.split(',')[-1].strip())
    df = df[df['country'] != excluded_country]

    df = df[df['title'].str.contains(search_term, case=False, na=False)]
    print(df.head())

    # Group and count jobs by country
    country_counts = df['country'].value_counts().reset_index()
    country_counts.columns = ['country', 'job_count']

    # Filter out countries with less than 5 jobs
    country_counts = country_counts[country_counts['job_count'] >= 5]
    top_countries = country_counts.head(15)

 # Create the plot
    fig = px.bar(
        top_countries,
        x='job_count',
        y='country',
        orientation='h',
        title=f'Job Distribution for "{search_term}" Outside {excluded_country}',
        labels={'job_count': 'Number of Jobs', 'country': 'Country'},
        height=600,
        width=800
    )

    fig.update_traces(
        marker=dict(line=dict(width=1, color='black')), 
        hoverinfo='y+x' 
    )

    fig.update_layout(
        yaxis=dict(categoryorder='total ascending', showticklabels=True),
        margin=dict(l=50, r=10, t=50, b=10), 
        title_x=0.5, 
    )

    return fig
