import itertools
from typing import NamedTuple, Dict, List

import ndjson
import requests


class Tweet(NamedTuple):
    id: int
    text: str
    source: str
    created_at: str
    is_retweet: bool


def parse_raw_tweet(tweet: Dict) -> Tweet:
    return Tweet(
        int(tweet['id_str']),
        tweet['text'],
        tweet['source'],
        tweet['created_at'],
        tweet['is_retweet']
    )


def flatten(super_list: List[List]) -> List:
    return list(itertools.chain(*super_list))


def main():
    urls_to_query = (f'http://trumptwitterarchive.com/data/realdonaldtrump/{year}.json' for year in range(2009, 2020))
    responses = [requests.get(url).json() for url in urls_to_query]

    tweets = list(sorted(flatten(responses), key=lambda tw: int(tw['id_str'])))
    print(len(tweets))

    output_file = '../data/trump_tweets.ndjson'
    with open(output_file, 'w') as f:
        ndjson.dump(tweets, f)


if __name__ == '__main__':
    main()
