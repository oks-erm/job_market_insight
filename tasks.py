



# 11111111111111





# @celery_app.task
# @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
# def scrape_linkedin_data(url, keywords, location, namespace):
#     print(f"Scraping FROM CELERY APP")
#     try:
#         # Set a custom User-Agent header to mimic a real web browser
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

#         progress_queue = Queue()
#         linkedin_scraper(url, 0, namespace, headers=headers)

#         # Scraping is complete, update the job data after scraping
#         job_data = get_job_data(keywords, location)

#         if not job_data.empty:
#             # If there is existing data (after scraping)
#             search_dataframe = plots.create_search_dataframe(
#                 keywords, location)
#             new_skills_plot = plots.create_top_skills_plot(
#                 search_dataframe, keywords, location)
#             new_top_cities_plot = plots.create_top_cities_plot(
#                 search_dataframe, max_cities=10, keywords=keywords, location=location)

#             # Emit the new plots to the specific client through the WebSocket
#             socketio.emit('update_plot', {
#                 'top_skills_json': new_skills_plot.to_json(),
#                 'top_cities_json': new_top_cities_plot.to_json(),
#             }, namespace=namespace)
    
#         else:
#             socketio.emit('no_data', {
#                 'progress': 100,
#                 'message': 'Fetching data, please wait...'
#             }, namespace=namespace)

#         # Scraping is complete *for the frontend*
#         socketio.emit('scraping_completed', namespace=namespace)

#     except requests.exceptions.HTTPError as e:
#         print(f"Error occurred while scraping job description: {str(e)}")
#         print(traceback.format_exc())
#         raise e

