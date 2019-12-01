FROM python:3-slim

RUN pip3 install psycopg2-binary tweepy python-dotenv ndjson
ADD TrumpTwitterArchivist.py /

# This should be overwritten in the 'docker run' command for running dumps
CMD python3 TrumpTwitterArchivist.py update
