import itertools
from datetime import datetime
from typing import NamedTuple, Dict, List

import ndjson
import requests


class Tweet(NamedTuple):
    # This is slightly different than the 'Tweet' namedtuple used elsewhere for ease of json serialization
    id: int
    text: str
    source: str
    created_at: str
    is_retweet: bool


def parse_raw_tweet_from_trumptwitterarchive(tweet: Dict) -> Tweet:
    return Tweet(
        int(tweet['id_str']),
        tweet['text'],
        tweet['source'],
        tweet['created_at'],  # No point in parsing to datetime since it's just getting written to json
        tweet['is_retweet'] or tweet['text'].startswith('RT @')  # Not all retweets are marked correctly with the bool
    )


def parse_raw_tweet_from_us(tweet: Dict) -> Tweet:
    return Tweet(
        int(tweet['id']),
        tweet['text'],
        tweet['source'],
        tweet['created_at'],  # No point in parsing to datetime since it's just getting written to json
        tweet['is_retweet'] or tweet['text'].startswith('RT @')  # Not all retweets are marked correctly with the bool
    )


def flatten(super_list: List[List]) -> List:
    return list(itertools.chain(*super_list))


def get_tweets_by_year(year: int) -> List[Tweet]:
    url = f'http://trumptwitterarchive.com/data/realdonaldtrump/{year}.json'
    response = requests.get(url)

    if response.text.startswith('<!DOCTYPE html>'):
        return []
    else:
        tweets = (parse_raw_tweet_from_trumptwitterarchive(raw_tweet) for raw_tweet in response.json())
        return list(sorted(tweets, key=lambda tw: tw.id))


def get_all_tweets_after_year(year: int):
    # 'after' is inclusive
    all_tweets = []

    while True:
        tweets = get_tweets_by_year(year)
        if len(tweets) > 0:
            all_tweets.extend(tweets)
            year += 1
        else:
            break

    return list(sorted(all_tweets, key=lambda tw: tw.id))


def get_all_tweets() -> List[Tweet]:
    return get_all_tweets_after_year(2009)


def full_dump(output_file: str) -> None:
    tweets = get_all_tweets()
    tweet_dicts = [tweet._asdict() for tweet in tweets]  # For json serialization

    with open(output_file, 'w') as f:
        ndjson.dump(tweet_dicts, f)


# This exists so that we won't overwrite data we have in case something happens to trumptwitterarchive.com
def add_new_tweets_to_dump(output_file: str) -> None:
    with open(output_file, 'r') as f:
        existing_raw_tweets = ndjson.load(f)

    existing_tweets = [parse_raw_tweet_from_us(tweet) for tweet in existing_raw_tweets]
    existing_tweet_ids = set(tweet.id for tweet in existing_tweets)

    if len(existing_tweets) > 0:
        newest_tweet_year = datetime.strptime(existing_tweets[-1].created_at, '%a %b %d %H:%M:%S %z %Y').year
    else:
        newest_tweet_year = 2009

    maybe_new_tweets = get_all_tweets_after_year(newest_tweet_year)
    new_tweets = (tweet for tweet in maybe_new_tweets if tweet.id not in existing_tweet_ids)

    all_tweets = itertools.chain(existing_tweets, new_tweets)
    tweet_dicts = [tweet._asdict() for tweet in all_tweets]  # For json serialization

    with open(output_file, 'w') as f:
        ndjson.dump(tweet_dicts, f)
