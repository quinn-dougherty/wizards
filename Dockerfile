FROM jupyter/scipy-notebook

RUN conda install -c conda-forge prefect tqdm \
  && conda install -c anaconda mypy

USER root

ENTRYPOINT ["/bin/bash"]
