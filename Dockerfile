FROM python:3.12-slim

WORKDIR /app
# VOLUME ["/data"]

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_DATA_DIR=/home/data/mii

# Install dependencies
RUN apt-get update && \
    apt-get install -y graphviz && \
    apt-get install -y wget && \
    rm -rf /var/lib/apt/lists/*
# Create home area for Azure WEB APP STORAGE
# Deal with path in entrypoint
# RUN mkdir -p /home/data && ln -s /home/data /data
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt 

# SHELL ["conda", "run", "-n", "mlayer", "/bin/bash", "-c"]

COPY . /app/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
