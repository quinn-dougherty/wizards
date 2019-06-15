#!/usr/bin/env python

from typing import List
import sqlite3
from contextlib import contextmanager
import pandas as pd # type: ignore

##############################
##############################
### * * * GLOBALS * * * *  ###
##############################
##############################

PROJECTS_CSV_PATH = 'projects-1318.csv'
SURVEY_CSV_PATH = 'survey-0350.csv'
SQL = '0350.sqlite3'

MAX_PREFS = 6

RANKS_NAMES: List[str] = [x + '_proj_choice'
                          for x
                          in ('first', 'second', 'third', 'fourth', 'fifth', 'sixth')]
STRONG_SEP: str = ' || ' # because a comma is too weak
# FIRST: int = 1 # index, consult the data you get
# LAST: int = 39 # index, consult the data you get


##############################
##############################
### * * * UTILITIES * * * * ##
##############################
##############################

def project_str_optional_clean(x):
    ''' option as in maybe "either fail or succeed", but this function is _mandatory_

    Any misbehaving characters you find, put them in here. '''
    try:
        return x.replace(',', '').replace('"', '')
    except AttributeError:
        return x

def proj_prefs(xs: str, strong_sep: str=STRONG_SEP) -> List[str]:
    '''

    NOTICE: we filter out 'Hybrid' projects here AND in io_init.read_in_projects '''
    return [x for x in xs.split(strong_sep) if x!='None' and 'DS Web Hybrid' not in x]

def people_prefs(xs: str) -> List[str]:
    try:
        return [x for x in xs.split(',')]
    except AttributeError:
        return []

##############################
##############################
### * * * * PANDAS * * * * ##
##############################
##############################

def read_in_projects(filename: str) -> pd.DataFrame:
   '''reads the projects csv. '''
   dat = (pd.read_csv(filename)
               .rename(columns={'Name': 'proj_name'})
               [['proj_name', 'max_staff']])

   return (dat#[["Hybrid" not in x for x in dat.proj_name]]
           .assign(proj_name = dat.proj_name.apply(project_str_optional_clean),

                      Web = None,
                      DS = None,
                      iOS = None,

                      max_Web = dat.max_staff.apply(lambda s: int(s[0])),
                      min_Web = dat.max_staff.apply(lambda s: int(s[0]) - 3
                                                    if int(s[0]) != 0
                                                    else 99),
                      max_DS = dat.max_staff.apply(lambda s: int(s[2])),
                      min_DS = dat.max_staff.apply(lambda s: int(s[2]) - 1
                                                    if int(s[2]) != 0
                                                    else 99),
                      max_iOS = dat.max_staff.apply(lambda s: int(s[4])),
                      min_iOS = dat.max_staff.apply(lambda s: int(s[4]) - 1
                                                    if int(s[4]) != 0
                                                    else 99),
                      surplus_popularity = 0)
           .fillna('')
           .drop('max_staff', axis=1)
           )[["DS Web Hybrid" not in x for x in dat.proj_name]]

def read_in_survey(filepath: str,
                   #first: int = FIRST,
                   #last_plus_one: int = LAST + 1,
                   ranks_names: List[str] = RANKS_NAMES,
                   strong_sep: str = STRONG_SEP) -> pd.DataFrame:

    dat = (pd.read_csv(filepath)
             #.drop(range(first))#.drop(range(last_plus_one, 110))
             .rename(columns={'Name': 'person_name',
                              'Track': 'track',
                              '1st Project Choice': ranks_names[0],
                              '2nd Project Choice': ranks_names[1],
                              '3rd Project Choice': ranks_names[2],
                              '4th Project Choice (optional)': ranks_names[3],
                              '5th Project Choice (optional)': ranks_names[4],
                              '6th Project Choice (optional)': ranks_names[5],
                              '3 Preferred Students': 'friends',
                              "Students You DON'T want to work with (optional)": 'enemies',
                              "Submission Time": 'timestamp'
                             })
            [['person_name', 'timestamp', 'track'] + ranks_names + ['friends', 'enemies']]
             .assign(assigned=None))

    to_keep = (dat.track=="DS") | (dat.track=="Web")

    ranks = dat[ranks_names].applymap(project_str_optional_clean).assign(rank_order=None).fillna("None")

    return (dat.assign(**{**{'rank_order': [strong_sep.join(ranks[feat][k]
                                                            for feat
                                                            in ranks_names)
                                            for k in dat.index],
                             'person_name': dat.person_name.apply(lambda s: s.replace('"', ''))},
                         **{feat: dat[feat].apply(project_str_optional_clean)
                            for feat
                            in ranks_names}})
            .drop(ranks_names, axis=1)
            .sort_values(by='timestamp'))[to_keep]

# call reader functions
survey_df = read_in_survey(SURVEY_CSV_PATH)

projects_df = read_in_projects(PROJECTS_CSV_PATH)

NUM_PEOPLE = survey_df.shape[0]
##############################
##############################
### * * * SQL INIT * * * *  ##
##############################
##############################

@contextmanager
def db_access(sqlite3_file):
    conn = sqlite3.connect(sqlite3_file)
    yield conn
    conn.commit()
    conn.close()

def init_reset(db_prefix: str):
    # init dbs.
    with db_access(db_prefix + SQL) as db:
        c = db.cursor()

        print(f"num_passes: {db_prefix[0]}", end='  .....  ')

        survey_df.to_sql("survey", db, index=False, if_exists='replace')
        print("wrote survey_df to table survey", end='  .....  ')

        projects_df.to_sql("projects", db, index=False, if_exists='replace')
        print("wrote projects_df to table projects")
    pass
