import requests
from time import sleep

from adapters.cache import cache_factory
from adapters.db import db_factory


class BaseRequestAdapter:
    def __init__(self):
        self.cache = cache_factory()
        self.db = db_factory()


    async def retry_request(self, url: str, params, response: requests.Response):
        count = 1
        retry_token = None

        while response.status_code != 200:
            sleep(count)

            response = requests.get(url, params=params)
            count *= 2

        return response, retry_token
