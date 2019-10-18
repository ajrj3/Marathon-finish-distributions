from requests import get
from requests import codes
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import time
from scipy.stats import percentileofscore
from scipy.stats import scoreatpercentile

# define get functions that download html page content
def log_error(e):
    print(e)

    
def page_get(base_url, page_idx):
    param_grid = {'page': page_idx}
    try:
        with closing(get(base_url, stream=True, params=param_grid)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None
            
    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None

    
def is_good_response(resp):
    return resp.status_code == codes.ok


# define scraping function that takes html page content from Strava's race webpage, and downloads data
# into a dataframe
def download_race_stats(race_url):
    pages = np.arange(1,1500,1)
    data = []
    for page in pages:
        raw_html = page_get(race_url, page)
        # break from loop if last page is reached
        if raw_html == None:
            break
        html_soup = BeautifulSoup(raw_html,'html.parser')
        results_table = html_soup.find('table', {'id': 'results-table'})

        for element in results_table:
            if element.name == 'thead' and page == 1:
                header_row = element.find('tr')
                header_row = header_row.get_text().split('\n')
                header_row = list(filter(lambda x: x != '', header_row))
            if element.name == 'tbody':
                athlete_data = element.find_all('tr')

        for row in athlete_data:
            rank = row.find('td', {'class': 'athlete-rank'}).get_text(r"\n", strip=True)
            name = row.find('td', {'class': 'athlete-name'}).get_text(r"\n", strip=True)
            gender = row.find('td', {'class': 'athlete-gender'}).get_text(r"\n", strip=True)
            age = row.find('td', {'class': 'athlete-age'}).get_text(r"\n", strip=True)
            finish = row.find('td', {'class': 'finish-time'}).get_text(r"\n", strip=True)
            pace = row.find('td', {'class': 'finish-pace'}).get_text(r"\n", strip=True)
            activity = row.find('td', {'class': 'athlete-activity'}).get_text(r"\n", strip=True)
            
            selected_row_data = [rank, name, gender, age, finish, pace, activity]
            data.append(selected_row_data)
        
    results_df = pd.DataFrame(data, columns=header_row)
    return results_df


# converts time object to minutes as a float
def time_to_float(t):
    return t.hour*60 + t.minute + t.second/60


# inverse of the time_to_float function
def float_to_time(minutes):
    return time(round(minutes/60), round(minutes%60), round(60*(minutes-round(minutes))))


# finish time data imported as string. Define function that converts string format 
# to datetime and also to float (for processing)
def clean_raw_df(raw_df):
    cleaned_df = raw_df.copy(deep=True)
    cleaned_df['Finish'] = pd.to_datetime(cleaned_df['Finish'],infer_datetime_format=True, errors='coerce')
    cleaned_df.drop(cleaned_df[pd.isna(cleaned_df['Finish'])].index, axis=0, inplace=True)
    cleaned_df['Finish'] = pd.Series([val.time() for val in cleaned_df['Finish']])  # remove date from datetime object
    cleaned_df.drop(cleaned_df[cleaned_df['Finish'] > time(7,0,0)].index, axis=0, inplace=True) # exclude errorneous entries beyond cut-off time
    cleaned_df['Finish (mins)'] = cleaned_df['Finish'].apply(time_to_float)
    return cleaned_df


# paste race url below, then scrape and clean data
chicago_url = r'https://www.strava.com/running_races/2782?hl=en-GB'
chicago_raw_df = download_race_stats(chicago_url)
chicago_df = clean_raw_df(chicago_raw_df)

chicago_percentiles = [scoreatpercentile(chicago_df['Finish (mins)'],np.arange(0,101,1))]

# plot percentiles and finish time distributions
times = np.arange(60,391,5)
fig, axs = plt.subplots(1,2, figsize=(12,6))
axs[1] = sns.distplot(chicago_df['Finish (mins)'], bins=times, kde_kws={"lw": 3})
axs[1].set_ylabel('Estimated Density Function')
axs[1].set_title('Chicago Marathon: Distribution of Finish Times', pad=10, fontweight=550)
axs[0].scatter(np.arange(0,101,1), chicago_percentiles, label='Chicago Marathon')
axs[0].set_ylabel('Finish Time (mins)')
axs[0].set_xlabel('Percentile')
axs[0].set_title('Chicago Marathon: Percentile Distribution', pad=10, fontweight=550)
plt.show()
