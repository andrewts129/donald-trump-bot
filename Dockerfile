FROM python:3.7-slim

RUN mkdir /app
WORKDIR /app

ADD requirements.txt DonaldTrumBot.py ./
ADD utils utils/
ADD namedtuples namedtuples/

RUN pip3 install -r requirements.txt && python3 -m nltk.downloader punkt averaged_perceptron_tagger
