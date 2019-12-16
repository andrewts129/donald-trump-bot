import re
from datetime import datetime

from namedtuples.Tweet import Tweet


def is_retweet(tweet: Tweet) -> bool:
    return tweet.is_retweet


def not_from_trump_device(tweet: Tweet) -> bool:
    if tweet.source in {'Twitter for Android', 'Twitter Web Client'}:
        return False
    elif tweet.source == 'Twitter for iPhone':
        return tweet.created_at < datetime.strptime('Feb 01 2017 +0000', '%b %d %Y %z')
    else:
        return True


def is_quote(tweet: Tweet) -> bool:
    bad_starts = ('"@', 'Via @')
    commonly_quoted = {'Albert Einstein', 'Aristotle', 'Benjamin Franklin'}
    return tweet.text.startswith(bad_starts) or any((person in tweet.text) for person in commonly_quoted) \
        or (re.match(r'^[“|\"].*[”|\"]\s*[–|\-].*$', tweet.text) is not None)


def is_short_reply(tweet: Tweet) -> bool:
    return tweet.text.startswith('@') and len(tweet.text.split(' ')) <= 5


def too_old(tweet: Tweet) -> bool:
    return tweet.created_at < datetime.strptime('Jan 01 2011 +0000', '%b %d %Y %z')


def is_just_link(tweet: Tweet) -> bool:
    return len(tweet.text.split(' ')) == 1 and tweet.text.startswith('http')


def should_use_tweet(tweet: Tweet) -> bool:
    tests = (is_retweet, not_from_trump_device, is_quote, is_short_reply, too_old, is_just_link)
    return not any(test(tweet) for test in tests)
