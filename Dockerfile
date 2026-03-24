FROM python:3.12-alpine

WORKDIR /app
VOLUME ["/data"]

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN apk --no-cache add wget
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt 

# SHELL ["conda", "run", "-n", "mlayer", "/bin/bash", "-c"]

COPY . /app/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
