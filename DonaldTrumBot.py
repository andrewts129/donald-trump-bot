#!/usr/bin/env python3
import os
import pickle
import sys
from timeit import default_timer as timer

import tweepy
from dotenv import load_dotenv

from utils.Model import train_model_from_file
from utils.TweetBuilder import create_tweet
from utils.TweetDownloader import add_new_tweets_to_dump
from utils.TweetPoster import get_tweet_ids_to_reply_to, post_reply_tweet, should_tweet_now, post_tweet

# TODO logging
load_dotenv()


def tweet_command() -> None:
    # TODO configurable
    model_file = 'data/model.pkl'
    min_between_wakeups = 5
    target_avg_tweets_per_day = 2.5
    force_tweet = False

    with open(model_file, 'rb') as fp:
        model = pickle.load(fp)

    auth = tweepy.OAuthHandler(consumer_key=os.environ["TW_CONSUMER_KEY"],
                               consumer_secret=os.environ["TW_CONSUMER_SECRET"])
    auth.set_access_token(key=os.environ["TW_ACCESS_TOKEN"],
                          secret=os.environ["TW_ACCESS_SECRET"])
    api = tweepy.API(auth)

    for tweet_id in get_tweet_ids_to_reply_to(api):
        tweet = create_tweet(model, 200)  # TODO 240?
        post_reply_tweet(api, tweet, tweet_id)

    if force_tweet or should_tweet_now(min_between_wakeups, target_avg_tweets_per_day):
        tweet = create_tweet(model, 240)
        post_tweet(api, tweet)


def train_command() -> None:
    # TODO make these configurable
    input_file = 'data/trump_tweets.ndjson'
    output_file = 'data/model.pkl'

    model = train_model_from_file(input_file)
    with open(output_file, 'wb') as fp:
        pickle.dump(model, fp)


def update_command() -> None:
    output_file = 'data/trump_tweets.ndjson'  # TODO configurable
    add_new_tweets_to_dump(output_file)


def test_tweet_command() -> None:
    # TODO make these configurable
    input_file = 'data/trump_tweets.ndjson'
    num_tweets = 10

    train_time_start = timer()
    model = train_model_from_file(input_file)
    train_time_total = timer() - train_time_start

    tweet_time_start = timer()
    tweets = []
    for i in range(0, num_tweets):
        tweets.append(create_tweet(model, 240))
    tweet_time_total = timer() - tweet_time_start

    print(f'Model training time: {train_time_total:.2f}s')
    print(f'Tweet building time: {tweet_time_total:.2f}s')
    print()
    print(f'Shortest Tweet: {min(len(tweet) for tweet in tweets)}')
    print(f'Longest Tweet:  {max(len(tweet) for tweet in tweets)}')
    print()
    for tweet in tweets:
        print(tweet)


def main():
    exit_status = 1

    if len(sys.argv) < 2:
        print("Specify one or more commands ('tweet', 'train', 'update', or 'test_tweet')")
    else:
        command = sys.argv[1]
        if command == 'tweet':
            tweet_command()
            exit_status = 0
        elif command == 'train':
            train_command()
            exit_status = 0
        elif command == 'update':
            update_command()
            exit_status = 0
        elif command == 'test_tweet':
            test_tweet_command()
            exit_status = 0
        else:
            print('Invalid command')

    exit(exit_status)


if __name__ == '__main__':
    main()
