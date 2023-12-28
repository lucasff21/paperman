from typing import List

from lingua import Language, LanguageDetectorBuilder
from nltk import download, WordNetLemmatizer
from nltk.corpus import stopwords


class NTLKService():
    def __init__(self) -> None:
        self.wnl = WordNetLemmatizer()
        self.languages = [Language.PORTUGUESE, Language.ENGLISH]
        self.language_detector = LanguageDetectorBuilder.from_all_languages().build()
    
    
    @staticmethod
    def download_resources() -> None:
        download('stopwords')
        download('wordnet')


    def clean(self, target: List[str]) -> List[str]:       
        combined_text = ' '.join(target)
        words = combined_text.replace("/", " ").split()
        unique_words_list = list(set(words))

        try:
            cachedStopwords = stopwords.words('portuguese') + stopwords.words('english')
        except LookupError:
            self.download_resources()
            cachedStopwords = stopwords.words('portuguese') + stopwords.words('english')

        no_stopwords = list(set(unique_words_list) - set(cachedStopwords))
        
        try:
            clean_list = [self.wnl.lemmatize(item).lower() for item in no_stopwords]
        except LookupError:
            self.download_resources()
            clean_list = [self.wnl.lemmatize(item).lower() for item in no_stopwords]

        return self.clean_query_subject_languages(clean_list)
    
    
    def clean_query_subject_languages(self, query_subjects: List[str]) -> List[str]:
        return [subject for subject in query_subjects if self.language_detector.detect_language_of(subject) in self.languages]
