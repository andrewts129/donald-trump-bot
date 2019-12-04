#!/usr/bin/env python3
import sys
from datetime import datetime
from typing import Dict, Iterable

import ndjson

from Model import Model, Tweet, Token
from TweetValidator import should_use_tweet


def parse_raw_tweet(raw_tweet: Dict) -> Tweet:
    return Tweet(
        id=int(raw_tweet['id']),
        text=raw_tweet['text'],
        source=raw_tweet['source'],
        created_at=datetime.strptime(raw_tweet['created_at'], '%a %b %d %H:%M:%S %z %Y'),
        is_retweet=raw_tweet['is_retweet']
    )


def join_tokens(tokens: Iterable[Token]) -> str:
    return ' '.join(token.word for token in tokens)  # TODO more sophisticated


if __name__ == '__main__':
    with open('data/trump_tweets.ndjson', 'r') as f:
        raw_tweets = ndjson.load(f)

    tweets = (parse_raw_tweet(tweet) for tweet in raw_tweets)
    tweets = [tweet for tweet in tweets if should_use_tweet(tweet)]

    model = Model(tweets)

    chain = model.generate_tokens(100)
    print(join_tokens(chain))

    print('done!')
    sys.exit(0)
