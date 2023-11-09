from typing import List

from nltk import download, WordNetLemmatizer
from nltk.corpus import stopwords


class NTLKService():
    def __init__(self) -> None:
        self.wnl = WordNetLemmatizer()
    
    
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
        
        clean_list = [self.wnl.lemmatize(item).lower() for item in no_stopwords]

        return clean_list
