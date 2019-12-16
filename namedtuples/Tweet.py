from datetime import datetime
from typing import NamedTuple


class Tweet(NamedTuple):
    id: int
    text: str
    source: str
    created_at: datetime
    is_retweet: bool
