from datetime import datetime
from typing import NamedTuple, Dict

_DATE_STRING_FORMAT = '%a %b %d %H:%M:%S %z %Y'


class Tweet(NamedTuple):
    id: int
    text: str
    source: str
    created_at: datetime
    is_retweet: bool


def encode_tweet_for_json(tweet: Tweet) -> Dict:
    result = tweet._asdict()
    result['created_at'] = result['created_at'].strftime(_DATE_STRING_FORMAT)
    return result


def tweet_json_decode_hook(tweet_json: Dict):
    return Tweet(
        tweet_json['id'] if 'id' in tweet_json else int(tweet_json['id_str']),
        tweet_json['text'],
        tweet_json['source'],
        datetime.strptime(tweet_json['created_at'], _DATE_STRING_FORMAT),
        tweet_json['is_retweet'] or tweet_json['text'].startswith('RT @')  # Not all retweets are marked with the bool?
    )
