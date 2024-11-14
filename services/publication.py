from datetime import datetime
from typing import Dict, List, Optional, Union

from lingua import Language, LanguageDetectorBuilder

from adapters.db import db_factory
from adapters.dblp import DBLPAdapter
from adapters.orcid import ORCIDAdapter
from nlp.nltk import NTLKService
from schemas.publication import Evaluation, Publication
from schemas.user import User
from services.user import UserService
from word_embedding.gensim import build_search_query, extract_best_match


class PublicationService():
	def __init__(self) -> None:
		self.dblp_adapter = DBLPAdapter()
		self.orcid_adapter = ORCIDAdapter()
		self.user_service = UserService()
		self.ntlk_service = NTLKService()
		self.languages = [Language.PORTUGUESE, Language.ENGLISH]
		self.language_detector = LanguageDetectorBuilder.from_all_languages().build()
		self.db = db_factory()


	async def get_publications(self, id: str) -> List[Publication]:
		user = self.user_service.get_user(id)

		summary = None
		publications = []

		for source in user.sources:
			if source.service == "orcid":
				summary = await self.orcid_adapter.get_user_summary(source.url)

		if summary:
			for subject in summary:
				subject_topics = build_search_query(subject)
				subject_publications = []

				for topic in subject_topics:
					topic_publications = await self.dblp_adapter.get_publications(topic)
					subject_publications.extend(topic_publications)

				subject_publications = self.sanitize_publications(subject_publications)

				best_publication = None

				if subject_publications:
					best_publication = await self.get_best_match(subject_publications, subject, user)

				if best_publication:
					publications.append(best_publication)

				if len(publications) == 3:
					return publications

		return publications


	async def get_best_match(self, publications: List[Publication], subject: str, user: User) -> Union[Publication, None]:
		now = datetime.now()

		publications = [publication for publication in publications if not self.publication_already_recommended(user, publication) and publication.year > (now.year - 5)]

		if publications:
			return await extract_best_match(publications, subject)

		return None


	@staticmethod
	def publication_already_recommended(user: User, publication: Publication) -> bool:
		return f"{publication.title}:{publication.year}" in user.recommendations


	async def demo(self, orcid: str) -> List[Publication]:
		now = datetime.now()

		publications = []

		summary = await self.orcid_adapter.get_user_summary(orcid)

		if summary:
			for subject in summary:
				subject_topics = build_search_query(subject)
				subject_publications = []

				for topic in subject_topics:
					topic_publications = await self.dblp_adapter.get_publications(topic)
					subject_publications.extend(topic_publications)

				subject_publications = self.sanitize_publications(subject_publications)

				best_publication = None

				if subject_publications:
					subject_publications = [publication for publication in subject_publications if publication.year < (now.year - 5)]

					best_publication = await extract_best_match(subject_publications, subject)

				if best_publication:
					publications.append(best_publication)

				if len(publications) == 3:
					return publications

		return publications


	def sanitize_publications(self, publications: List[Dict]) -> List[Publication]:
		sanitized_publications = []

		for publication in publications:
			if 'authors' in publication['info']:
				author = publication['info']['authors']['author']

				if isinstance(author, Dict):
					author['pid'] = author['@pid']
					author['name'] = author['text']
					authors = publication['info']['authors']
					publication['info']['authors'] = [authors['author']]
				elif isinstance(author, List):
					for author in publication['info']['authors']['author']:
						author['pid'] = author['@pid']
						author['name'] = author['text']

				if 'author' in publication['info']['authors']:
					publication['info']['authors'] = publication['info']['authors']['author']
			else:
				publication['info']['authors'] = []

			if 'venue' in publication['info'] and not type(publication['info']['venue']) == str:
				publication['info']['venue'] = '; '.join(publication['info']['venue'])

			sanitized_publications.append(Publication(**publication['info']))

		publication_titles = [publication.title for publication in sanitized_publications]

		title_languages = self.language_detector.detect_languages_in_parallel_of(publication_titles)
		not_desired_languages = [index for index, item in enumerate(title_languages) if item not in self.languages]
		
		for index in reversed(not_desired_languages):
			sanitized_publications.pop(index)

		return sanitized_publications
	

	def evaluation(self, name: str, evaluations: List[Evaluation], comments: Optional[str]) -> None:
		data = {
			"name": name,
			"evaluations": evaluations,
			"comments": comments,
		}

		self.db.set_evaluation(data)
