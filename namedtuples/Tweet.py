from datetime import datetime
from typing import NamedTuple


class Tweet(NamedTuple):
    id: int
    text: str
    source: str
    created_at: datetime
    is_retweet: bool


def tweet_string_to_datetime(s: str) -> datetime:
    return datetime.strptime(s, '%a %b %d %H:%M:%S %z %Y')


def tweet_datetime_to_string(dt: datetime) -> str:
    return dt.strftime('%a %b %d %H:%M:%S %z %Y')
