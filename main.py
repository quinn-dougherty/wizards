#!/usr/bin/env python
from typing import Optional, List
from argparse import ArgumentParser
from pandas import DataFrame # type: ignore
from numpy import arange, array # type: ignore
from prefect import task, Flow, Parameter# type: ignore
from prefect.engine.executors import DaskExecutor # type: ignore

from reports import bars, summary_txt
from solver import solve, flip
from io_init import NUM_PEOPLE

def mk_df(dat: DataFrame, weight: float) -> DataFrame:
    ''' make the results of the different number of iterations into a dataframe. '''
    dat_ = (dat
            .T
            .rename(columns={0: 'unpopular_remaining',
                             1: 'people_unassigned'})
           )

    return dat_.assign(cost = weight*dat_.unpopular_remaining + (1 - weight) * dat_.people_unassigned)

def mk_parser() -> ArgumentParser:

    parser = ArgumentParser()
    parser.add_argument("--idx-range",
                        help="most amount of iterations to check",
                        type=int,
                        default=7)
    parser.add_argument("--once",
                        help="only check one number of iterations",
                        type=Optional[int],
                        default=None)
    parser.add_argument("--weight", help="""weight x assigned to
                                             unpopular project minimization
                                             importance. high and dry minimi
                                             zation importance follows as 1-x.""",
                        type=float,
                        default=0.7)

    return parser

if __name__=='__main__':

    args = mk_parser().parse_args()

    idx = range(args.idx_range)

    # Parallelization with prefect
    with Flow("solver") as flow:

        # the parallel executor
        executor = DaskExecutor(local_processes=True)

        if args.once:
            passes: List[int] = [int(args.once)]
        else:
            passes: List[int] = list(idx)

        # iterable task
        results_ = solve.map(Parameter("passes"))

        # run session
        ran = flow.run(passes=passes, executor=executor)

        results = ran.result[results_].result

        df: DataFrame = mk_df(DataFrame({k+1: v
                                         for k,v
                                         in enumerate(results)}),
                              args.weight)

    df.to_csv('output/results.csv')

    best_idx: int = int(df.cost.astype(float).idxmin())

    best: str = f"According to our cost calculation, the best match is {best_idx} passes. "

    print(df, '\n')

    print(best)

    bars(df, args.weight)

    for i in (best_idx - 1, best_idx, best_idx + 1):
        try:
            summary_txt(results=df, idx=i, num_people=NUM_PEOPLE, best_str=best)
        except:
            print(f"couldn't summarize {idx}")
