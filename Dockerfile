FROM python:3.14

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=run.py

EXPOSE 5000

CMD flask db upgrade && flask run --host=0.0.0.0 --port=5000