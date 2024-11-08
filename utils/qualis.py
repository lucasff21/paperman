from csv import DictReader
from os import path
from re import sub
from typing import Dict, List

from pandas import read_csv

from utils import QUALIS_SCORES


def update_files() -> None:
    conferences_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTZsntDnttAWGHA8NZRvdvK5A_FgOAQ_tPMzP7UUf-CHwF_3PHMj_TImyXN2Q_Tmcqm2MqVknpHPoT2/pub?output=csv"
    periodics_url = "https://docs.google.com/spreadsheets/d/10sObNyyL7veHGFbOyizxM8oVsppQoWV-0ALrDr8FxQ0/export?format=csv&gid=204503454"
    
    output_folder = "./resources/qualis/"
    
    conferences_df = read_csv(conferences_url, on_bad_lines='skip')
    periodics_df = read_csv(periodics_url, on_bad_lines='skip')
    
    conferences_df.to_csv(path.join(output_folder, "conferences.csv"), index=False)
    periodics_df.to_csv(path.join(output_folder, "periodics.csv"), index=False)


def load_conferences() -> List[Dict]:
    with open("./resources/qualis/conferences.csv") as conferences:
        conferences_reader = list(DictReader(conferences))
        
    return conferences_reader


def get_conference_score(conference_name: str) -> float:
    conferences = load_conferences()
    
    try:
        conference = list(filter(lambda x: sub(r"\([^)]*\)", "", x.get("evento", "")).lower().strip() == conference_name.lower().strip(), conferences))[0]
        qualis = conference["Qualis_Final"]
        return QUALIS_SCORES[qualis]
    except IndexError:
        return 0


def load_periodics() -> List[Dict]:
    with open("./resources/qualis/periodics.csv") as periodics:
        periodics_reader = list(DictReader(periodics))
        
    return periodics_reader


def get_periodic_score(periodic_name: str) -> float:
    periodics = load_periodics()
    
    try:
        periodic = list(filter(lambda x: sub(r"\([^)]*\)", "", x.get("periodico", "")).lower().strip() == periodic_name.lower().strip(), periodics))[0]
        qualis = periodic['Qualis_Final']
        return QUALIS_SCORES[qualis]
    except IndexError:
        return 0
    except KeyError:
        return 0
