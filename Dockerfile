FROM python:3.6-slim

RUN pip install tweepy numpy requests

ADD DonaldTrumBot.py /

CMD python /DonaldTrumBot.py