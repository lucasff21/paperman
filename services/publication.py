from datetime import datetime
from typing import List, Union

from adapters.dblp import DBLPAdapter
from adapters.orcid import ORCIDAdapter
from nlp.nltk import NTLKService
from schemas.publication import Publication
from schemas.user import User
from services.user import UserService
from word_embedding.gensim import apply_word_embedding, extract_best_match


class PublicationService():
    def __init__(self) -> None:
        self.dblp_adapter = DBLPAdapter()
        self.orcid_adapter = ORCIDAdapter()
        self.user_service = UserService()
        self.ntlk_service = NTLKService()
        
    
    def get_publications(self, id: str) -> List[Publication]:
        user = self.user_service.get_user(id)
        
        query_subjects = []
        
        for source in user.sources:
            if source.service == "orcid":
                summary = self.orcid_adapter.get_user_summary(source.url)
                query_subjects.extend(summary)
            
        query_subjects = self.ntlk_service.clean(query_subjects)
        
        publications = []
        
        for subject in query_subjects:
            subject_best_match = apply_word_embedding(subject)
            subject_publications = self.dblp_adapter.get_publications(subject_best_match)
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
