import logging
import requests

from time import sleep

from adapters.cache import cache_factory
from adapters.db import db_factory


class BaseRequestAdapter:
    def __init__(self):
        self.cache = cache_factory()
        self.db = db_factory()


    def retry_request(self, url: str, params, response: requests.Response):
        count = 1

        while response.status_code != 200:
            logging.warning(f"Retry #{count} to {url} (status code {response.status_code}) with params {params}")
            
            sleep(count)

            response = requests.get(url, params=params)
            count *= 2

        return response
