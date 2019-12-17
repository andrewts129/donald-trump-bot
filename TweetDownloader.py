import itertools
from typing import List

import ndjson
import requests

from namedtuples.Tweet import Tweet, tweet_json_decode_hook, encode_tweet_for_json


def _flatten(super_list: List[List]) -> List:
    return list(itertools.chain(*super_list))


def _get_tweets_by_year(year: int) -> List[Tweet]:
    url = f'http://trumptwitterarchive.com/data/realdonaldtrump/{year}.json'
    response = requests.get(url)

    if response.text.startswith('<!DOCTYPE html>'):
        return []
    else:
        tweets = response.json(object_hook=tweet_json_decode_hook)
        return list(sorted(tweets, key=lambda tw: tw.id))


def _get_all_tweets_after_year(start_year: int):
    # 'after' is inclusive
    all_tweets = []

    for year in itertools.count(start_year):
        tweets = _get_tweets_by_year(year)
        if len(tweets) > 0:
            all_tweets.extend(tweets)
        else:
            break

    return list(sorted(all_tweets, key=lambda tw: tw.id))


def _get_all_tweets() -> List[Tweet]:
    return _get_all_tweets_after_year(2009)


def full_dump(output_file: str) -> None:
    tweets = _get_all_tweets()
    with open(output_file, 'w') as f:
        ndjson.dump((encode_tweet_for_json(tweet) for tweet in tweets), f)


# This exists so that we won't overwrite data we have in case something happens to trumptwitterarchive.com
def add_new_tweets_to_dump(output_file: str) -> None:
    with open(output_file, 'r') as f:
        existing_tweets = ndjson.load(f, object_hook=tweet_json_decode_hook)

    existing_tweet_ids = set(tweet.id for tweet in existing_tweets)
    newest_tweet_year = existing_tweets[-1].created_at.year if len(existing_tweets) > 0 else 2009

    maybe_new_tweets = _get_all_tweets_after_year(newest_tweet_year)
    new_tweets = (tweet for tweet in maybe_new_tweets if tweet.id not in existing_tweet_ids)

    all_tweets = itertools.chain(existing_tweets, new_tweets)
    with open(output_file, 'w') as f:
        ndjson.dump((encode_tweet_for_json(tweet) for tweet in all_tweets), f)
