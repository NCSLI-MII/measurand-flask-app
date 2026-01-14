FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements_pip_v2.txt /app/
RUN pip install --no-cache-dir -r requirements_pip_v2.txt 

# SHELL ["conda", "run", "-n", "mlayer", "/bin/bash", "-c"]

COPY . /app/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
