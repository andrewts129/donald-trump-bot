#!/usr/bin/env python3
import re
import sys
from datetime import datetime
from typing import Dict, Iterable

import ndjson

from Model import Model, Tweet, Token


def parse_raw_tweet(raw_tweet: Dict) -> Tweet:
    return Tweet(
        id=int(raw_tweet['id']),
        text=raw_tweet['text'],
        source=raw_tweet['source'],
        created_at=datetime.strptime(raw_tweet['created_at'], '%a %b %d %H:%M:%S %z %Y'),
        is_retweet=raw_tweet['is_retweet']
    )


def should_use_tweet(tweet: Tweet) -> bool:
    # TODO this should be its own file probably

    def has_good_source(tweet: Tweet) -> bool:
        if tweet.source in {'Twitter for Android', 'Twitter Web Client'}:
            return True
        elif tweet.source == 'Twitter for iPhone':
            return tweet.created_at > datetime.strptime('Feb 01 2017 +0000', '%b %d %Y %z')
        else:
            return False

    def is_quote(tweet: Tweet) -> bool:
        bad_starts = ('"@', 'Via @')
        return tweet.text.startswith(bad_starts) or re.fullmatch(r'^[“|\"].*[”|\"]\s*[–|\-].*$', tweet.text) is not None

    def is_short_reply(tweet: Tweet) -> bool:
        return tweet.text.startswith('@') and len(tweet.text.split(' ')) <= 5

    def too_old(tweet: Tweet) -> bool:
        return tweet.created_at < datetime.strptime('Jan 01 2011 +0000', '%b %d %Y %z')

    def is_just_link(tweet: Tweet) -> bool:
        return len(tweet.text.split(' ')) == 1 and tweet.text.startswith('http')

    return not tweet.is_retweet and has_good_source(tweet) and not is_quote(tweet) and not is_short_reply(tweet) and not too_old(tweet) and not is_just_link(tweet)


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
