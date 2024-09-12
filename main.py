import requests
import json
import datetime as dt
import time
import logging

from decouple import config
from scheduler import Scheduler

API_URL = config("API_URL")


def main(logger):

    # obtain users from json file
    users= []
    try:
        with open('credentials.json') as json_file:
            json_file = json.load(json_file)
            credentials = json_file['credentials']
            users = credentials
    except Exception as e:
        logger.error(f"Failed to open credentials file: {e}")

    for user in users:
        # login
        response = None
        try:
            response = requests.post(f'{API_URL}auth/hris/login', json={
                'employee_number': user['employee_number'],
                'password': user['password']
            })
        except Exception as e:
            logger.error(f"Failed to login user {user['employee_number']}: {e}")
            continue

        if response.status_code != 200:
            logger.error(f"Failed to login user {user['employee_number']}: {response.json()}")
            continue
        
        user_token = response.json()['data']['token']

        # check if timed in
        dashboard_response = None
        try:
            dashboard_response = requests.post(f'{API_URL}hris/dashboard', headers={
                'Authorization': f'Bearer {user_token}'
            })  
        except Exception as e:
            logger.error(f"Failed to get dashboard for user {user['employee_number']}: {e}")
            continue

        if dashboard_response.status_code != 200:
            logger.error(f"Failed to get dashboard for user {user['employee_number']}: {dashboard_response.json()}")
            continue
        

        time_in = dashboard_response.json()['data']['attendance']['time_in']
        time_out = dashboard_response.json()['data']['attendance']['time_out']

        if time_in == None:
            continue
        # perform time out
        time_out_response = None
        try:
            time_out_response = requests.post(f'{API_URL}hris/attendance/submit', headers={
                'Authorization': f'Bearer {user_token}'
            })  
        except Exception as e:
            logger.error(f"Failed to time out user {user['employee_number']}: {e}")
            continue

        if time_out_response.status_code != 200:
            logger.error(f"Failed to time out user {user['employee_number']}: {time_out_response.json()}")
            continue
        
        logger.info(f"Successfully timed out user {user['employee_number']}")


if __name__ == "__main__":
    logging.basicConfig(
        filename='./app.log',
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info(f"Starting Auto out at {dt.datetime.now()}")

    scheduler = Scheduler()
    scheduler.daily(dt.time(hour=20, minute=39, second=1), main, args=[logger])

    while True:
        try:
            scheduler.exec_jobs()
        except Exception as e:
            print(f"Failed to execute jobs: {e}")
            logging.error(f"Failed to execute jobs: {e}")
        
        logger.info('tick')

        time.sleep(10)
