FROM jupyter/scipy-notebook

RUN conda install -c conda-forge prefect tqdm

USER root

ENTRYPOINT ["/bin/bash"]
