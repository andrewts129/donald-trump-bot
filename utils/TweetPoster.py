from datetime import datetime, timedelta
from random import random, choice
from typing import Set

import tweepy
from tweepy import API, Status


def _get_liked_tweet_ids(api: API) -> Set[int]:
    return set(tweet.id for tweet in tweepy.Cursor(api.favorites).items())


def _is_retweet(tweet: Status) -> bool:
    return hasattr(tweet, 'retweeted_status')


def _get_mentions_tweet_ids(api: API) -> Set[int]:
    mentions = (tweet for tweet in tweepy.Cursor(api.mentions_timeline).items() if not _is_retweet(tweet))

    one_day_ago = datetime.today() - timedelta(days=1)
    recent_mentions = (tweet for tweet in mentions if tweet.created_at > one_day_ago)

    return set(mention.id for mention in recent_mentions)


def should_tweet_now(min_between_wakeups: float, target_avg_tweets_per_day: float) -> bool:
    wakeups_per_day = (24 * 60) / min_between_wakeups
    chance_to_tweet = target_avg_tweets_per_day / wakeups_per_day
    return chance_to_tweet > random()


def post_tweet(api: API, tweet: str) -> None:
    api.update_status(tweet)


def post_reply_tweet(api: API, tweet: str, status_id_to_reply_to: int) -> None:
    api.create_favorite(status_id_to_reply_to)  # To prevent from replying twice. Also just kinda funny

    user_to_reply_to = api.get_status(status_id_to_reply_to).author.screen_name
    api.update_status(f'@{user_to_reply_to} {tweet}', status_id_to_reply_to, auto_populate_reply_metadata=True)


def get_tweet_ids_to_reply_to(api: API) -> Set[int]:
    liked_tweet_ids = _get_liked_tweet_ids(api)
    mentioned_tweet_ids = _get_mentions_tweet_ids(api)
    return mentioned_tweet_ids - liked_tweet_ids


def get_random_follower(api: API) -> str:
    follower_ids = list(tweepy.Cursor(api.followers_ids).items())
    random_follower_id = choice(follower_ids)
    random_follower = api.get_user(user_id=random_follower_id)
    return random_follower.screen_name
