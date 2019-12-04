#!/usr/bin/env python3
# TODO: After finding trumptwitterarchive.com's API, this is now mostly redundant. Remove?
import os
import sys
from datetime import datetime
from typing import NamedTuple, List, Dict

import ndjson
import psycopg2
import tweepy
from dotenv import load_dotenv


class Tweet(NamedTuple):
    id: int
    text: str
    source: str
    created_at: datetime
    is_retweet: bool


def get_newest_stored_tweet_id(connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute('SELECT MAX(id) FROM tweets;')
        return cursor.fetchone()[0]


def get_recent_trump_tweets(api, since_id, n) -> List[Tweet]:
    statuses = tweepy.Cursor(api.user_timeline, screen_name='realDonaldTrump', since_id=since_id, tweet_mode='extended', count=n).items()
    return [parse_raw_tweet(status) for status in statuses]


def parse_raw_tweet(tweet) -> Tweet:
    return Tweet(
        id=tweet.id,
        text=tweet.full_text,
        source=tweet.source,
        created_at=tweet.created_at,
        is_retweet=hasattr(tweet, 'retweeted_status')
    )


def store_tweets(connection, tweets: List[Tweet]) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            'INSERT INTO tweets VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;',
            tweets)
        connection.commit()


def retrieve_tweets(connection) -> List[Tweet]:
    with connection.cursor() as cursor:
        cursor.execute('SELECT id, text, source, created_at, is_retweet FROM tweets;')
        return [Tweet(*result) for result in cursor.fetchall()]


def tweet_tuple_to_dict(tweet: Tweet) -> Dict:
    return {
        'id': tweet.id,
        'text': tweet.text,
        'source': tweet.source,
        'created_at': tweet.created_at.strftime('%a %b %d %H:%M:%S %z %Y'),
        'is_retweet': tweet.is_retweet
    }


if __name__ == '__main__':
    exit_status = 1

    load_dotenv()

    db_connection = psycopg2.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
                                     password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
                                     port=os.getenv('DB_PORT'))

    command = sys.argv[1]
    if command == 'update':
        twitter_auth = tweepy.OAuthHandler(os.getenv('TW_CONSUMER_KEY'), os.getenv('TW_CONSUMER_SECRET'))
        twitter_auth.set_access_token(os.getenv('TW_ACCESS_TOKEN'), os.getenv('TW_ACCESS_SECRET'))
        twitter_api = tweepy.API(twitter_auth)

        newest_stored_tweet_id = get_newest_stored_tweet_id(db_connection)
        new_tweets = get_recent_trump_tweets(twitter_api, newest_stored_tweet_id, 200)

        if len(new_tweets) > 0:
            print('Storing tweets with the following IDs:')
            for tweet in new_tweets:
                print(tweet.id)

            store_tweets(db_connection, new_tweets)
        else:
            print('No new tweets to store')

        exit_status = 0  # Success
    elif command == 'dump':
        dump_file_name = sys.argv[2]

        tweets = retrieve_tweets(db_connection)
        tweets_as_dicts = (tweet_tuple_to_dict(tweet) for tweet in tweets)  # For JSON serialization

        with open(dump_file_name, 'w') as f:
            ndjson.dump(tweets_as_dicts, f)

        print(f'Dumped {len(tweets)} tweets to {dump_file_name}')
        exit_status = 0  # Success
    else:
        print('Unrecognized command')
        exit_status = 1  # Failure

    db_connection.close()
    sys.exit(exit_status)
