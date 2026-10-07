FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY backend/requirements.txt /tmp/backend-requirements.txt
COPY Storyteller/requirements.txt /tmp/storyteller-requirements.txt
COPY HistoicalEventExplainer/requirements.txt /tmp/explainer-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/backend-requirements.txt \
    -r /tmp/storyteller-requirements.txt \
    -r /tmp/explainer-requirements.txt

COPY . /workspace

ENV PYTHONPATH=/workspace/backend
WORKDIR /workspace/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
