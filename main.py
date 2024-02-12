from typing import Optional, List
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
        logfile.write(f'{datetime.now()}\t\t{data}\n')


class User:
    _last_out: Optional[datetime] = None
    _auth_token: Optional[str] = None
    _schedule_out: Optional[datetime] = None


    def __init__(self, employee_number: str, password: str):
        self.employee_number: str = employee_number
        self.password: str = password
        self._schedule_out = None
        self.assign_schedule()


    def __str__(self) -> str:
        return f"{self.employee_number}, Schedule: {self._schedule_out}"


    @property
    def should_out(self) -> bool:
        if self._schedule_out is None:
            return False
        return self._schedule_out < datetime.now()


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
            write_log(f'{self.employee_number} failed to login')
            write_log(response.text)
            return self

        parsed = json.loads(response.text)
        self._auth_token = parsed["data"]["token"]
        write_log(f'{self.employee_number} logged in')
        return self


    def clock_out(self) -> Self:
        if self._auth_token is None:
            self.login()

        if not self.should_out:
            return self

        response = requests.post(
            f"{API_URL}/api/v1/hris/attendance/submit",
            headers={"Authorization": f"Bearer {self._auth_token}"},
        )
        if response.status_code != 200:
            self.login()

        self._last_out = datetime.now()
        write_log(f"{self.employee_number} Last out: {self._last_out}")
        self.assign_schedule()
        return self


def load_credentials() -> List[User]:
    with open("credentials.json") as json_file:
        parsed = json.loads(json_file.read())
        write_log("Loaded credentials")
        return [
            User(item["employee_number"], item["password"])
            for item in parsed["credentials"]
        ]


def main():
    write_log(f'Started on {datetime.now()}')
    users: list[User] = load_credentials()
    while True:
        for user in users:
            user.clock_out()
        time.sleep(60)


if __name__ == "__main__":
    main()
