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
    # TODO put this somewhere else
    output = ' '.join(token.word for token in tokens)

    replacements = [
        (' ,', ','), (' .', '.'), (' ?', '?'), (' !', '!'), (' :', ':'), (' ;', ';'), ('... ', '...'), (' …', '…'),
        ('. @', '.@'), ('- -', '--'), ('U. S.', 'U.S.'), ('A. G.', 'A.G.'), ('D. C.', 'D.C.'),
        ('P. M.', 'P.M.'), ('A. M.', 'A.M.'), ('0, 0', '0,0'), ('$ ', '$'), (' %', '%'), ('MS - 13', 'MS-13'),
        ('# ', '#'), ('w /', 'w/'), (' / ', '/'), ('“', '"'), ('”', '"'), ('’', "'"), ("n ' t", "n't"),
        (" ' s", "'s"), (" ' v", "'v"), (" ' re", "'re"), ("' 0", "'0")
    ]
    for replacement_pair in replacements:
        output = output.replace(*replacement_pair)

    # TODO do something about unmatched parenthesis/quotes
    return output.strip()


def train_model(tweets_ndjson_filename: str) -> Model:
    with open(tweets_ndjson_filename, 'r') as f:
        raw_tweets = ndjson.load(f)

    tweets = (parse_raw_tweet(tweet) for tweet in raw_tweets)
    tweets = (tweet for tweet in tweets if should_use_tweet(tweet))

    model = Model(tweets)
    return model


def main():
    # TODO remove this
    model = train_model('data/trump_tweets.ndjson')

    for i in range(0, 10):
        chain = model.generate_tokens(100)
        print(join_tokens(chain))
        print()

    sys.exit(0)


if __name__ == '__main__':
    main()
