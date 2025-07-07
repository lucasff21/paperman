import requests
from http import HTTPStatus

from decouple import config

from adapters.request import BaseRequestAdapter
from exceptions import DependencyException


class ORCIDAdapter(BaseRequestAdapter):
    def __init__(self) -> None:
        self.ORCID_CLIENT_ID = config("ORCID_CLIENT_ID")
        self.ORCID_CLIENT_SECRET = config("ORCID_CLIENT_SECRET")
        self.ORCID_TOKEN = config("ORCID_TOKEN")
        self.ORCID_API_URL = "https://pub.orcid.org/v3.0/:id/record"
        super().__init__()


    async def get_public_records(self, id: str):
        url = self.ORCID_API_URL.replace(":id", id)
        headers = {
            "Authorization": self.ORCID_TOKEN,
            "Content-Type": "application/orcid+json"
        }

        public_records = await self.cache.get_orcid_public_records(id)

        if not public_records:
            r = requests.get(
                url=url,
                headers=headers
            )

            if r.status_code == 200:
                await self.cache.set_orcid_public_records(id, r.text)
                return r.json()

            raise DependencyException(f"orcid (status code {r.status_code})", status_code=HTTPStatus.FAILED_DEPENDENCY)

        return public_records


    async def get_user_summary(self, id: str):
        public_records = await self.get_public_records(id)

        subjects = []

        work_affiliations = public_records["activities-summary"]["works"]["group"]
        for affiliation in work_affiliations:
            for index in affiliation["work-summary"]:
                if not index.get("title"):
                    continue

                data = index["title"]["title"]["value"]

                if data:
                    subjects.append(data)

        return subjects
