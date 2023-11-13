import requests

from http import HTTPStatus

from decouple import config

from adapters.cache import Cache
from exceptions import DependencyException


class ORCIDAdapter:
    def __init__(self) -> None:
        self.ORCID_CLIENT_ID = config("ORCID_CLIENT_ID")
        self.ORCID_CLIENT_SECRET = config("ORCID_CLIENT_SECRET")
        self.ORCID_TOKEN = config("ORCID_TOKEN")
        self.ORCID_API_URL = "https://pub.orcid.org/v3.0/:id/record"
        self.cache = Cache()
        
    
    def get_public_records(self, id: str):
        url = self.ORCID_API_URL.replace(':id', id)
        headers = {
            "Authorization": self.ORCID_TOKEN,
            "Content-Type": "application/orcid+json"
        }
        
        public_records = self.cache.get_orcid_public_records(id)
        
        if not public_records:
            r = requests.get(
                url=url,
                headers=headers
            )
            
            if r.status_code == 200:
                self.cache.set_orcid_public_records(id, r.text)
                return r.json()

            raise DependencyException(f"orcid (status code {r.status_code})", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
        return public_records
    
    
    def get_user_summary(self, id: str):
        public_records = self.get_public_records(id)
        
        subjects = []
        
        education_affiliations = public_records['activities-summary']['educations']['affiliation-group']
        for affiliation in education_affiliations:
            for index in affiliation['summaries']:
                data = index['education-summary']['department-name']

                if data:
                    subjects.append(data)
                
        employment_affiliations = public_records['activities-summary']['employments']['affiliation-group']
        for affiliation in employment_affiliations:
            for index in affiliation['summaries']:
                data = index['employment-summary']['role-title']

                if data:
                    subjects.append(data)

        work_affiliations = public_records['activities-summary']['works']['group']
        for affiliation in work_affiliations:
            for index in affiliation['work-summary']:
                data = index['title']['title']['value']

                if data:
                    subjects.append(data)
        
        return subjects
