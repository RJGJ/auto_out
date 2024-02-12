from typing import Optional
from typing_extensions import Self
from decouple import config
from datetime import datetime
import requests
import json
import time
import random

API_URL = config("API_URL")
TIME_WINDOW_START = config("TIME_WINDOW_START")
TIME_WINDOW_END = config("TIME_WINDOW_END")


def write_log(data: str):
    with open("./.log", "a") as logfile:
        logfile.write(f'{data}\n')


class User:
    _last_out: Optional[datetime]
    _auth_token: Optional[str]
    _schedule_out: Optional[datetime]


    def __init__(self, employee_number: str, password: str):
        self.employee_number: str = employee_number
        self.password: str = password
        self._schedule_out = None


    def __str__(self) -> str:
        return f"{self.employee_number}, Schedule: {self._schedule_out}"


    @property
    def should_out(self) -> bool:
        if self._schedule_out is None:
            return False
        return self._schedule_out < datetime.now()
    

    def start(self):
        self.login().assign_schedule().clock_out()


    def assign_schedule(self) -> Self:
        now = datetime.now()
        window_start = datetime.strptime(TIME_WINDOW_START, "%H:%M").timestamp()
        window_end = datetime.strptime(TIME_WINDOW_END, "%H:%M").timestamp()
        schedule = datetime.fromtimestamp(
            random.uniform(window_start, window_end)
        ).replace(
            year=now.year,
            month=now.month,
            day=now.day,
        )
        self._schedule_out: datetime = schedule
        write_log(f'{self.employee_number} assigned at: {self._schedule_out}')
        return self


    def login(self) -> Self:
        response = requests.post(
            f"{API_URL}/api/v1/auth/hris/login",
            json={
                "employee_number": self.employee_number,
                "password": self.password,
            },
        )

        if response.status_code != 200:
            return self

        parsed = json.loads(response.text)
        self._auth_token = parsed["data"]["token"]
        write_log(f'{self.employee_number} logged in')
        return self


    def clock_out(self) -> Self:
        if self._auth_token is None:
            return self

        if not self.should_out:
            return self

        response = requests.post(
            f"{API_URL}/api/v1/hris/attendance/submit",
            headers={"Authorization": f"Bearer {self._auth_token}"},
        )
        if response.status_code != 200:
            return self
        self._last_out = datetime.now()

        self.assign_schedule()
        write_log(f"{self.employee_number} Last out: {self._last_out}")
        return self


def load_credentials() -> list[User]:
    with open("credentials.json") as json_file:
        parsed = json.loads(json_file.read())
        return [
            User(item["employee_number"], item["password"])
            for item in parsed["credentials"]
        ]


def main():
    users: list[User] = load_credentials()
    while True:
        for user in users:
            user.start()
        time.sleep(60)


if __name__ == "__main__":
    main()
