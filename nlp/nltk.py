from typing import List

from lingua import Language, LanguageDetectorBuilder
from nltk import download, WordNetLemmatizer, word_tokenize
from nltk.corpus import stopwords
from re import compile

class NTLKService():
    def __init__(self) -> None:
        self.wnl = WordNetLemmatizer()
        self.languages = [Language.PORTUGUESE, Language.ENGLISH]
        self.language_detector = LanguageDetectorBuilder.from_all_languages().build()


    @staticmethod
    def download_resources() -> None:
        download('stopwords')
        download('wordnet')
        download('punkt')
        download('punkt_tab')


    def clean_subject(self, target: str) -> str:
        try:
            target = word_tokenize(target)
        except LookupError:
            self.download_resources()
            target = word_tokenize(target)

        unique_words_list = list({word.lower():"" for word in target})

        try:
            cached_stopwords = stopwords.words('portuguese') + stopwords.words('english')
        except LookupError:
            self.download_resources()
            cached_stopwords = stopwords.words('portuguese') + stopwords.words('english')

        no_stopwords = [word for word in unique_words_list if word not in cached_stopwords]

        symbol_pattern = compile(r'[^a-zA-Z0-9\s]')
        no_symbols = [word for word in no_stopwords if not symbol_pattern.search(word)]

        try:
            lemmatized_list = [self.wnl.lemmatize(item).lower() for item in no_symbols]
        except LookupError:
            self.download_resources()
            lemmatized_list = [self.wnl.lemmatize(item).lower() for item in no_symbols]

        return ' '.join([word for word in lemmatized_list if self.language_detector.detect_language_of(word) in self.languages])


    def clean_publication_title(self, target: str) -> List[str]:
        try:
            target = word_tokenize(target)
        except LookupError:
            self.download_resources()
            target = word_tokenize(target)

        unique_words_list = list({word.lower():"" for word in target})

        try:
            cached_stopwords = stopwords.words('portuguese') + stopwords.words('english')
        except LookupError:
            self.download_resources()
            cached_stopwords = stopwords.words('portuguese') + stopwords.words('english')

        no_stopwords = [word for word in unique_words_list if word not in cached_stopwords]

        symbol_pattern = compile(r'[^a-zA-Z0-9\s]')
        no_symbols = [word for word in no_stopwords if not symbol_pattern.search(word)]

        try:
            clean_list = [self.wnl.lemmatize(item).lower() for item in no_symbols]
        except LookupError:
            self.download_resources()
            clean_list = [self.wnl.lemmatize(item).lower() for item in no_symbols]

        return [word for word in clean_list if self.language_detector.detect_language_of(word) in self.languages]
