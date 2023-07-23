
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
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


    # Extract city and country names from the 'location' column
    def extract_place_names(location_str):
        places = GeoText(location_str)
        city = places.cities[0] if places.cities else ''
        country = places.countries[0] if places.countries else ''
        return city, country

    # Split the 'location' column into 'city' and 'country' columns
    df_filled['city'] = df_filled['location'].apply(
        lambda x: x.split(',')[0].strip())
    df_filled['country'] = df_filled['location'].apply(
        lambda x: x.split(',')[-1].strip())
    df_filled.drop(columns=['location'], inplace=True)

    # Sort the DataFrame by the 'date' column in descending order
    df_sorted = df_filled.sort_values('date', ascending=False)

    # Return the DataFrame for the search query
    return df_sorted


def create_top_skills_plot(search_dataframe,  keywords=None, location=None, fig=None):
    max_skills = 20
    top_skills_df = get_top_skills(search_dataframe, max_skills)

    # Sort the DataFrame in descending order of frequency to have top skills on top
    top_skills_df = top_skills_df.sort_values(by='frequency', ascending=True)

    # Create the horizontal bar chart
    new_fig = px.bar(
        top_skills_df,
        x='frequency',
        y='skill',
        orientation='h',
        color='frequency',
        labels={'frequency': 'Frequency', 'skill': 'Skills'},
        title=f'Top {max_skills} skills for {keywords} jobs in {location}',
        height=600,  # Adjust the height of the figure as needed
        width=800,  # Adjust the width of the figure as needed
    )

    # Adjust the appearance of the bars
    new_fig.update_traces(
        # Add a thin black outline to the bars
        marker=dict(line=dict(width=1, color='black')),
        showlegend=False,  # Hide the legend
    )

    # Adjust the layout to display all 20 skill labels on the y-axis without being cut off
    new_fig.update_layout(
        yaxis=dict(categoryorder='total ascending', showticklabels=True),
        margin=dict(l=50, r=10, t=50, b=10),  # Reduce the margins
        title_x=0.5,  # Center the title along the x-axis
    )

    if fig is not None:
        # If the figure is provided, update its data with the new data
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
