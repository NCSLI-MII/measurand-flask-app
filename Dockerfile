FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements_pip_v3_py3.12.txt /app/
RUN pip install --no-cache-dir -r requirements_pip_v3_py3.12.txt 

# SHELL ["conda", "run", "-n", "mlayer", "/bin/bash", "-c"]

COPY . /app/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
