#!/usr/bin/env python

import matplotlib.pyplot as plt # type: ignore
plt.style.use('dark_background')
from pandas import DataFrame # type: ignore
from numpy import arange # type: ignore
from io_init import db_access, SQL
from typing import List, Tuple, Callable

def get_surplus_pop(db_prefix: str) -> List[Tuple[str, str]]:
    ''' get the surplus popularity of a project '''
    query_surplus_pop = "SELECT proj_name, surplus_popularity FROM projects WHERE surplus_popularity > 0"
    with db_access(db_prefix + SQL) as db:
        c = db.cursor()

        c.execute(query_surplus_pop)
        proj_surplus_pop = c.fetchall()

        #print(proj_surplus_pop)
        return proj_surplus_pop

def bars(results: DataFrame, weight):
    # create plot
    fig, ax = plt.subplots()
    index = results.index
    bar_width = 0.35
    opacity = 0.8

    rects1 = plt.bar(index,
                     results.unpopular_remaining,
                     bar_width,
                     alpha=opacity,
                     color='b',
                     label='Unpopular Remaining Projects')

    rects2 = plt.bar([x + bar_width for x in index],
                     results.people_unassigned,
                     bar_width,
                     alpha=opacity,
                     color='g',
                     label='People Unassigned')

    weighted_avg = plt.plot(index,
                            results.cost,
                            color='w',
                            label=f'Weighted sum cost: {weight} toward unpopular')

    plt.xlabel('Number of Passes Thru')
    plt.ylabel('Cost')
    plt.title('Results by Number of Passes')
    plt.xticks([x + bar_width for x in index], index)
    plt.legend()

    plt.savefig('output/cost.png')

def summary_txt(results: DataFrame,
                idx: int,
                num_people: int,
                best_str: str):
    '''writes a summary'''
    db_prefix: Callable[[int], str] = lambda passes: f"output/{passes}-passes-"

    best_idx: int = int(results.cost.astype(float).idxmin())

    surpluses: List[Tuple[str, str]] = get_surplus_pop(db_prefix(idx))

    with open(f'output/{idx}-passes-summary.txt', 'w') as f:

        f.write(best_str + '\n\n')
        f.write("------" + f" ACCORDING TO THE {idx} PASSES MATCH: " + "------")
        result = results.loc[idx]
        f.write(f"According to {idx} passes match, there are {result.unpopular_remaining} unpopular remaining projects\n\n")
        f.write(f"they are {result[2]}\n\n")
        f.write(f"and {result.people_unassigned} people unassigned, or {100 * (result.people_unassigned / num_people):.4}%\n\n")
        f.write("it only covered Web students. DS and iOS need to be done by hand. \n\n")
        f.write('\t')
        f.write('\n\t'.join(f"{proj[0]} has a surplus popularity score of {proj[1]}" for proj in surpluses))
        f.write('\n')

    print(f'wrote {idx}-passes-summary.txt')
    pass
