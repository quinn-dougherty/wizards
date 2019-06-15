# Wizards

[![Build Status](https://travis-ci.org/dwyl/esta.svg?branch=master)](https://travis-ci.org/quinn-dougherty/wizards)

[![Inline docs](http://inch-ci.org/github/quinn-dougherty/wizards.svg?branch=master)](http://inch-ci.org/github/quinn-dougherty/wizards)

Software for assigning students to capstone projects, for [Lambda School](https://lambdaschool.com/)'s Labs program

Wizards is an implementation of something like the [stable marriage problem](https://en.wikipedia.org/wiki/Stable_marriage_problem) or the
[resident matching service](https://www.carms.ca/), which differs crucially
because, for us, only one class of objects has preferences. In addition, there are
various customizations built on top of it, but at its core the solver is inspired by
those problem.  

# Usage

Currently, the user has to edit paths to csv files in `io_init.py`, after
downloading them from a suitably formatted survey (API specification coming
soon).  

It runs in Python 3.7 with Pandas and parallelization in [Prefect](https://docs.prefect.io/). If cloned with the Dockerfile,
just type

``` shell
docker build -t wizards-env .
docker run -it -v $(pwd):/home/jovyan/ wizards-env
\# python main.py
```

The command line arguments specify how wide a search over solver parameters and
the "weight" measuring how much you care about different aspects of the
solution. 

``` shell
\$ python main.py -h
usage: main.py [-h] [--idx-range IDX_RANGE] [--once ONCE] [--weight WEIGHT]

optional arguments:
  -h, --help            show this help message and exit
  --idx-range IDX_RANGE
                        most amount of iterations to check
  --once ONCE           only check one number of iterations
  --weight WEIGHT       weight x assigned to unpopular project minimization importance. high and dry minimi zation importance follows as 1-x.
```

It will report the best match according to its cost measure and two
neighboring matches in `.txt` files, show the change in cost over iterations in
`cost.png`, and write each matching as a `.sqlite3` file to browse results. I
recommend an app like [this](https://sqlitebrowser.org/) for easy perusing. 

# Code

It's parallelized as a Prefect task and compliant with [PEP
484](https://www.python.org/dev/peps/pep-0484/). 
