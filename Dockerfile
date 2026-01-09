FROM continuumio/miniconda3:latest

WORKDIR /app

COPY environment.yml /app/
RUN conda env create -f environment.yml && conda clean -afy

SHELL ["conda", "run", "-n", "mlayer", "/bin/bash", "-c"]

COPY . /app/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /tmp/miiflask

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
