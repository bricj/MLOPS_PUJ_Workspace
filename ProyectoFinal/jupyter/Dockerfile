FROM python:3.12

WORKDIR /jupyter_app
COPY ./app .

#ADD ./app /jupyter_app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

#WORKDIR /src/train_models
RUN uv sync --frozen
#RUN uv add -r requirements.txt
RUN pip install --no-cache-dir -r requirements.txt