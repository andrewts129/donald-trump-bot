from random import random
from typing import Set

import tweepy
from tweepy import API


def _get_liked_tweet_ids(api: API) -> Set[int]:
    return set(tweet.id for tweet in tweepy.Cursor(api.favorites).items())


def _get_mentions_tweet_ids(api: API) -> Set[int]:
    mentions = (tweet for tweet in tweepy.Cursor(api.mentions_timeline).items())
    return set(mention.id for mention in mentions if not hasattr(mention, 'retweeted_status'))


def should_tweet_now(min_between_wakeups: float, target_avg_tweets_per_day: float) -> bool:
    wakeups_per_day = (24 * 60) / min_between_wakeups
    chance_to_tweet = target_avg_tweets_per_day / wakeups_per_day
    return chance_to_tweet > random.random()


def post_tweet(api: API, tweet: str) -> None:
    api.update_status(tweet)


def post_reply_tweet(api: API, tweet: str, status_id_to_reply_to: int) -> None:
    user_to_reply_to = api.get_status(status_id_to_reply_to).author.screen_name
    # TODO do I need the string interpolation?
    api.update_status(f'@{user_to_reply_to} {tweet}', status_id_to_reply_to, auto_populate_reply_metadata=True)


def get_tweet_ids_to_reply_to(api: API) -> Set[int]:
    # TODO this is broken
    # liked_tweet_ids = _get_liked_tweet_ids(api)
    # mentioned_tweet_ids = _get_mentions_tweet_ids(api)
    # return mentioned_tweet_ids - liked_tweet_ids
    return set()
