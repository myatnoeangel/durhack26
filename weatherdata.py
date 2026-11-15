import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import date, timedelta
import matplotlib as mpl

cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

locations = {
    "London": [51.50, 0.12],
    "Tokyo": [35.69, 139.69],
    "New York" : [40.71, -74.01],
    "Shanghai" : [31.22, 121.46],
    "Sydney" : [-33.86, 151.20]
}

latitudes = [loc[0] for loc in locations.values()]
longitudes = [loc[1] for loc in locations.values()]

# url = "https://api.open-meteo.com/v1/forecast"
url = "https://archive-api.open-meteo.com/v1/archive"

end_date = date.today() - timedelta(days=1)
start_date = end_date - timedelta(days=365)


params = {
    "latitude": latitudes,
    "longitude": longitudes,
    "start_date": start_date.strftime("%Y-%m-%d"),
    "end_date": end_date.strftime("%Y-%m-%d"),
    "hourly": [
        "temperature_2m",
        "relative_humidity_2m"
    ],
}

responses = openmeteo.weather_api(url, params = params)

for i, response in enumerate(responses):
    location_name = list(locations.keys())[i]

    # current = response.Current()
    # current_time = pd.to_datetime(current.Time(), unit="s", utc=True)

    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
           start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
           end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
           freq = pd.Timedelta(seconds = hourly.Interval()),
           inclusive = "left"
        ),
        "temperature_2m": hourly_temperature_2m,
        "relative_humidity_2m": hourly_relative_humidity_2m
    }

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    hourly_dataframe.to_csv(f"weather_data_{location_name}.csv", index=False)


def getTemp(loc_name):
    for i, response in enumerate(responses):
        current_location = list(locations.keys())[i]

        if current_location.lower() == loc_name.lower():
            current = response.Current()
            temp = current.Variables(0).Value()

            return temp
    return None


def getPastYear(loc_name):

    location = next(
        (name for name in locations if name.lower() == loc_name.lower()),
        None
    )

    if location is None:
        raise ValueError(f"Location not found: {loc_name}")

    latitude, longitude = locations[location]

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=365)

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        # The order here must match the Variables(n) indexes below
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "cloud_cover"
        ],
        "timezone": "auto"
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    hourly = response.Hourly()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
        "precipitation": hourly.Variables(2).ValuesAsNumpy(),
        "cloud_cover": hourly.Variables(3).ValuesAsNumpy()
    }

    return pd.DataFrame(hourly_data)


def getAllPastYear():

    all_data = {}

    for location_name in locations:
        print(f"Fetching weather data for {location_name}...")

        all_data[location_name] = getPastYear(location_name)

    return all_data