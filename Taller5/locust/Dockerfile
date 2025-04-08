FROM python:3.12-slim

WORKDIR src/locust

COPY locustfile.py /src/locust
COPY requirements.txt /src/locust

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8089

CMD ["locust", "-f", "locustfile.py"]