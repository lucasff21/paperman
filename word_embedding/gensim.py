from re import findall, sub
from typing import List

from gensim.models import KeyedVectors
from numpy import dot
from numpy.linalg import norm
from multi_rake import Rake

from adapters.dblp import DBLPAdapter
from nlp.nltk import NTLKService
from schemas.publication import Publication
from utils.qualis import get_conference_score, get_periodic_score

def init_model() -> None:
    try:
        KeyedVectors.load("cbow_s100", mmap="r")
    except FileNotFoundError:
        model = KeyedVectors.load_word2vec_format("./resources/word2vec/cbow_s100.txt")
        model.init_sims(replace=True)
        model.save("cbow_s100")


def load_model():
    model = None
    
    try:
        model = KeyedVectors.load("cbow_s100", mmap="r")
    except FileNotFoundError:
        init_model()
        model = KeyedVectors.load("cbow_s100", mmap="r")

    return model


def euclidian_distance(target, subject):
    return norm(target - subject)


def cosine_similarity(target, subject):
    return dot(target, subject) / (norm(target) * norm(subject))


def apply_word_embedding(word) -> str:
    model = load_model()
    
    try:
        similar_words = model.most_similar(word)
    except KeyError:
        return word

    most_similar = max(similar_words, key=lambda x: x[1])
    return most_similar[0]


def build_search_query(subject: str):
    subject = sub(r'[^\x00-\x7f]', r'', subject)

    rake = Rake()
    keywords = rake.apply(subject)

    return [item[0] for item in keywords]


async def extract_best_match(publications: List[Publication], subject: str) -> Publication:
    ntlk_service = NTLKService()
    model = load_model()

    for publication in publications:
        venue_score = 0
        
        if publication.venue:
            try:
                venue_score = await get_venue_score(publication)
            except Exception:
                venue_score = 0  # Offline/timeout: ignora venue score
        
        title_similarity = 0
        
        for word in ntlk_service.clean_publication_title(publication.title):
            try:
                title_similarity += cosine_similarity(model[subject], model[word])
            except KeyError:
                pass
        
        publication.score = publication.year + venue_score + title_similarity
        
    return max(publications, key=lambda x: x.score)


async def get_venue_score(publication: Publication) -> float:
    dblp = DBLPAdapter()
    
    key = findall(r"^[A-Za-z]+/[A-Za-z]+", publication.key)
    if not key:
        return 0
    
    key = key[0]
    
    type = key.split("/")
    if not type:
        return 0
    
    type = type[0]
    
    venue = await dblp.get_venue(key)
    if not venue:
        return 0
    
    if type == "journals":
        return get_periodic_score(venue.info.venue)
    elif type == "conf":
        return get_conference_score(venue.info.venue)
    else:
        return 0
