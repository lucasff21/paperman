from datetime import datetime
from typing import List, Union

from adapters.dblp import DBLPAdapter
from adapters.orcid import ORCIDAdapter
from nlp.nltk import NTLKService
from schemas.publication import Publication
from schemas.user import User
from services.user import UserService
from word_embedding.gensim import build_search_query, extract_best_match


class PublicationService():
    def __init__(self) -> None:
        self.dblp_adapter = DBLPAdapter()
        self.orcid_adapter = ORCIDAdapter()
        self.user_service = UserService()
        self.ntlk_service = NTLKService()
        
    
    def get_publications(self, id: str) -> List[Publication]:
        user = self.user_service.get_user(id)
        
        summary = None
        publications = []
        
        for source in user.sources:
            if source.service == "orcid":
                summary = self.orcid_adapter.get_user_summary(source.url)
        
        if summary:
            for subject in summary:                
                subject_topics = build_search_query(subject)
                subject_publications = []
                
                for topic in subject_topics:
                    subject_publications.extend(self.dblp_adapter.get_publications(topic))
                
                best_publication = None
                
                if subject_publications:
                    best_publication = self.get_best_match(subject_publications, subject, user)

                if best_publication:
                    publications.append(best_publication)
                    
                if len(publications) == 3:
                    return publications
            
        return publications

    
    def get_best_match(self, publications: List[Publication], subject: str, user: User) -> Union[Publication, None]:
        now = datetime.now()
        
        for publication in publications:
            if self.publication_already_recommended(user, publication) or publication.year < (now.year - 5):
                publications.remove(publication)
        
        if publications:
            return extract_best_match(publications, subject)

        return None


    @staticmethod
    def publication_already_recommended(user: User, publication: Publication) -> bool:
        return f"{publication.title}:{publication.year}" in user.recommendations

    
    def demo(self, orcid: str) -> List[Publication]:
        now = datetime.now()
        
        publications = []
        
        summary = self.orcid_adapter.get_user_summary(orcid)
        
        if summary:
            for subject in summary:                
                subject_topics = build_search_query(subject)
                subject_publications = []
                
                for topic in subject_topics:
                    subject_publications.extend(self.dblp_adapter.get_publications(topic))
                
                best_publication = None
                
                if subject_publications:
                    subject_publications = [publication for publication in subject_publications if publication.year < (now.year - 5)]
                    best_publication = extract_best_match(subject_publications, subject)

                if best_publication:
                    publications.append(best_publication)
                    
                if len(publications) == 3:
                    return publications
            
        return publications
