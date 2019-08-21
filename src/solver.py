#!/usr/bin/env python

from typing import Dict, List, TypeVar, Tuple, Union
from collections import defaultdict
from functools import wraps
from numpy.random import choice, shuffle # type: ignore
from tqdm import tqdm # type: ignore
from prefect import task # type: ignore

from io_init import db_access, SQL, STRONG_SEP, proj_prefs, MAX_PREFS, init_reset
A = TypeVar('A')
B = TypeVar('B')

###########################
####                   ####
####       UTILS       ####
####                   ####
###########################

def dict_printer(F: Dict[str, str]) -> str:
    return '\n\t'.join(f"{key}: {value}" for key, value in F.items())

def preimage(b: B, f: Dict[str, B]) -> List[str]:
    ''' get the preimage of one item. '''
    return [a for a in f.keys() if f[a]==b]

def flip(surj: Dict[A, B]) -> Dict[B, List[A]]:
    ''' any surjection A -> B can be flipped into an injection B -> 2**A '''
    result: Dict[B, List[A]] = defaultdict(list)
    for key, value in surj.items():
        result[value].append(key)
    return result

###########################
####                   ####
####       GETTERS     ####
####                   ####
###########################

def get_rankorder(person: str, db_prefix: str) -> List[str]:
    '''docstring'''
    q = f"SELECT rank_order FROM survey WHERE person_name=\"{person}\""

    with db_access(db_prefix + SQL) as db:
        c = db.cursor()
        c.execute(q)
        X = c.fetchall()[0][0]
    return proj_prefs(X)

def get_person_proj_preferences_map(db_prefix: str) -> Dict[str, List[str]]:
    '''docstring'''
    get_people_names = "SELECT person_name, track FROM survey"

    with db_access(db_prefix + SQL) as db:
        c = db.cursor()
        c.execute(get_people_names)
        X = c.fetchall()

    return {t: get_rankorder(t[0], db_prefix=db_prefix)for t in X}

# high n dry
def get_unassigned(db_prefix: str) -> List[str]:
    get_unassigned = f"SELECT person_name FROM survey WHERE assigned=\"NULL\""

    with db_access(db_prefix + SQL) as db:
        c = db.cursor()
        c.execute(get_unassigned)
        unassigned = c.fetchall()

    return unassigned

def get_assignment(db_prefix: str) -> Dict[str, str]:
    '''return a map from people to projects'''
    get_people_assigned = "SELECT person_name, assigned FROM survey"

    with db_access(db_prefix + SQL) as db:
        c = db.cursor()
        c.execute(get_people_assigned)
        X = c.fetchall()
    return {t[0]: t[1] for t in X}

def get_unfriendlies(pers_name: str, db_prefix: str) -> List[str]:
    ''' take a person and return their listed unfriendlies '''
    get_persons_unfriendlies = f"SELECT enemies FROM survey WHERE person_name=\"{pers_name}\""

    with db_access(db_prefix + SQL) as db:
        c = db.cursor()
        c.execute(get_persons_unfriendlies)
        X = c.fetchall()[0][0]
    if X:
        return ''.join([x.replace('"', '') for x in X]).split(',')
    else:
        return []

def get_unpopulars(assgmnt: Dict[str, str], threshold: int = 4) -> List[str]:
    ''' return projects under a certain number of people

    This is implemented for the total team, not for parts of teams yet.
    '''
    return [key for key,value in flip(assgmnt).items() if len(value)<=threshold]

def mark_dropped(proj: str, db_prefix: str):
    ''' updates db with unpopulars to be dropped'''
    where = lambda feat: f"WHERE {feat}=\"{proj}\""
    projects_update = f"UPDATE projects SET (Web, DS, iOS)=(\"DROPPED\", \"DROPPED\", \"DROPPED\") {where('proj_name')}"
    survey_update = f"UPDATE survey SET assigned=\"NULL\" {where('assigned')}"
    with db_access(db_prefix + SQL) as db:
        c = db.cursor()

        c.execute(projects_update)
        c.execute(survey_update)
    pass



def drop_unpopulars(db_prefix: str):
    query_get_team_min = lambda team: f"""
        SELECT proj_name, min_{team}, max_{team}, {team}
        FROM projects
        WHERE {team}!="DROPPED" AND {team}!=""
        ORDER BY LENGTH({team})"""
    fetch = lambda c: [t for t in c.fetchall() if t[1] < 90]

    with db_access(db_prefix + SQL) as db:
        c = db.cursor()

        #c.execute(query_get_team_min('DS'))
        #DS_tup = fetch(c)

        c.execute(query_get_team_min('Web'))
        Web_tup = fetch(c)

        #c.execute(query_get_team_min('iOS'))
        #iOS_tup = fetch(c)

    #print(len(Web_tup), len(DS_tup), len(iOS_tup))i
    # print(Web_tup)
    #drop_DS = [t[0] for t in DS_tup if len(t[3].split(STRONG_SEP))-1 < t[1]]
    drop_Web = [t[0] for t in Web_tup if len(t[3].split(STRONG_SEP))-1 < t[1]]
    #drop_iOS = [t[0] for t in iOS_tup if len(t[3].split(STRONG_SEP))-1 < t[1]]

    # for proj in set(drop_DS + drop_Web + drop_iOS)
    for proj in drop_Web:
        yield mark_dropped(proj, db_prefix)
###########################
####                   ####
####       SOLVER      ####
####                   ####
###########################

def assign_to_nth(n: int,
                  db_prefix: str,
                  person_proj_preferences_map: Dict[str, List[str]]):

    for key, val in person_proj_preferences_map.items():
        try:
            nth = val[n]
        except IndexError:
            continue
        else:
            where_proj_name_is_nth = f"WHERE proj_name=\"{nth}\""
            where_person_name_is_key0 = f"WHERE person_name=\"{key[0]}\""
            get_track = f"SELECT track FROM survey {where_person_name_is_key0}"
            get_max_team = f"SELECT max_{key[1]} FROM projects {where_proj_name_is_nth}"
            get_team_so_far = f"SELECT {key[1]} FROM projects {where_proj_name_is_nth}"
            get_surplus_pop = f"SELECT surplus_popularity FROM projects {where_proj_name_is_nth}"
            get_assigned = f"SELECT assigned FROM survey {where_person_name_is_key0}"

            set_assigned_in_survey = f"UPDATE survey SET assigned = \"{nth}\" WHERE person_name=\"{key[0]}\""
            set_team_in_projects = lambda updated_team: f"UPDATE projects SET {key[1]}=\"{updated_team}\" {where_proj_name_is_nth}"
            set_surplus_pop = f"UPDATE projects SET surplus_popularity=surplus_popularity+(6-{n})/6 {where_proj_name_is_nth}"

            with db_access(db_prefix + SQL) as db:
                c = db.cursor()

                # get track name fro msurvey
                c.execute(get_track)
                track = c.fetchall()[0][0]

                # get max team size from projects
                c.execute(get_max_team)
                max_for_track = c.fetchall()[0][0]
                #print(max_for_track)

                # get team so far by track
                c.execute(get_team_so_far)
                team_so_far = c.fetchall()[0][0]

                if len(team_so_far.split(STRONG_SEP)) >= int(max_for_track):
                    c.execute(set_surplus_pop)
                elif team_so_far == 'DROPPED':
                    continue
                else:
                    c.execute(get_assigned)
                    assigned = c.fetchall()[0][0]
                    if assigned:
                        continue
                    else:
                        new_team = team_so_far + STRONG_SEP+key[0]
                        c.execute(set_assigned_in_survey)
                        c.execute(set_team_in_projects(new_team))
    pass

def _solve(person_proj_preferences_map: Dict[str, List[str]],
           iternum: int,
           db_prefix: str):
    for k in range(MAX_PREFS):
        assign_to_nth(k, db_prefix, person_proj_preferences_map)

###########################
####                   ####
####    REPORTERS      ####
####                   ####
###########################

def unfriendly_warning(assgnmnt: Dict[str, str], db_prefix: str) -> Dict[str, str]:
    '''  '''
    warnings = dict()
    for person, project in assgnmnt.items():
        i = set(get_unfriendlies(person, db_prefix)).intersection(set(preimage(project, assgnmnt)))
        if i:
            warnings[project] = f"{person} and {i} are paired together. "

    return warnings

###########################
####                   ####
####    ITER SOLVER    ####
####                   ####
###########################

@task
def solve(#unpopulars: List[str],
          passes: int = 3) -> Tuple[int, int, List[str]]:
    ''' the solver makes a pass, drops one of the unpopular projects that remains, and makes another pass '''

    db_prefix: str = f"output/{passes}-passes-"
    init_reset(db_prefix=db_prefix)

    drop = drop_unpopulars(db_prefix=db_prefix)

    person_proj_preferences_map = get_person_proj_preferences_map(db_prefix=db_prefix)

    # solve it initally
    _solve(person_proj_preferences_map, iternum=0, db_prefix=db_prefix)


    for k in tqdm(range(1, passes), desc=f"solving {passes} times"):
        try:
            drop.__next__() # drop one unpopular
        except StopIteration as e:
            #_solve(person_proj_preferences_map, iternum=k+1, db_prefix=db_prefix)
            break
        finally:
            _solve(person_proj_preferences_map, iternum=k, db_prefix=db_prefix)

    unassigned = get_unassigned(db_prefix=db_prefix)

    assignment = get_assignment(db_prefix=db_prefix)

    unpopulars = get_unpopulars(assgmnt=assignment)

    warnings = unfriendly_warning(assignment, db_prefix)

    print(f"\tunpopulars: {len(unpopulars)}")
    print(f"\tHigh and dry: {len(unassigned)}")
    print("\t"+dict_printer(warnings))
    return len(unpopulars), len(unassigned), unpopulars
