#!/usr/bin/env python3
import argparse
import os
import pickle
from timeit import default_timer as timer
from typing import Dict

import tweepy
from dotenv import load_dotenv

from utils.Model import train_model_from_file
from utils.TweetBuilder import create_tweet
from utils.TweetDownloader import add_new_tweets_to_dump
from utils.TweetPoster import get_tweet_ids_to_reply_to, post_reply_tweet, should_tweet_now, post_tweet

# TODO logging
load_dotenv()


def tweet_command(args: Dict) -> None:
    with open(args['model_file'], 'rb') as fp:
        model = pickle.load(fp)

    auth = tweepy.OAuthHandler(consumer_key=os.environ["TW_CONSUMER_KEY"],
                               consumer_secret=os.environ["TW_CONSUMER_SECRET"])
    auth.set_access_token(key=os.environ["TW_ACCESS_TOKEN"],
                          secret=os.environ["TW_ACCESS_SECRET"])
    api = tweepy.API(auth)

    for tweet_id in get_tweet_ids_to_reply_to(api):
        tweet = create_tweet(model, 200)  # TODO 240?
        post_reply_tweet(api, tweet, tweet_id)

    if args['force_tweet'] or should_tweet_now(args['min_between_wakeups'], args['target_avg_tweets_per_day']):
        tweet = create_tweet(model, 240)
        post_tweet(api, tweet)


def train_command(args: Dict) -> None:
    # TODO use partial fit method
    model = train_model_from_file(args['tweet_file'], args['min_ngram_length'], args['max_ngram_length'],
                                  args['lazy_fit'])
    with open(args['model_file'], 'wb') as fp:
        pickle.dump(model, fp)


def update_command(args: Dict) -> None:
    add_new_tweets_to_dump(args['tweet_file'])


def test_tweet_command(args: Dict) -> None:
    train_time_start = timer()
    model = train_model_from_file(args['tweet_file'], args['min_ngram_length'], args['max_ngram_length'],
                                  args['lazy_fit'])
    train_time_total = timer() - train_time_start

    tweet_time_start = timer()
    tweets = []
    for i in range(0, args['tweets_to_build']):
        tweets.append(create_tweet(model, 240))
    tweet_time_total = timer() - tweet_time_start

    print(f'Model training time: {train_time_total:.2f}s')
    print(f'Tweet building time: {tweet_time_total:.2f}s (Avg. {(tweet_time_total / len(tweets)):.2f}s / tweet)')
    print()
    print(f'Shortest Tweet: {min(len(tweet) for tweet in tweets)}')
    print(f'Longest Tweet:  {max(len(tweet) for tweet in tweets)}')
    print()
    for tweet in tweets:
        print(tweet)


def main():
    parser = argparse.ArgumentParser(description='Command line interface for @DonaldTrumBot')
    parser.add_argument('command', type=str, choices=['tweet', 'train', 'update', 'test_tweet'])

    parser.add_argument('--model_file', type=str, default='data/model.pkl')
    parser.add_argument('--tweet_file', type=str, default='data/trump_tweets.ndjson')
    parser.add_argument('--min_between_wakeups', type=float, default=10)
    parser.add_argument('--target_avg_tweets_per_day', type=float, default=2.5)
    parser.add_argument('--force-tweet', action='store_true')
    parser.add_argument('--min-ngram-length', type=int, default=2)
    parser.add_argument('--max-ngram-length', type=int, default=10)
    parser.add_argument('--tweets_to_build', type=int, default=10)
    parser.add_argument('--lazy-fit', action='store_true')

    args = vars(parser.parse_args())

    if args['command'] == 'tweet':
        tweet_command(args)
    elif args['command'] == 'train':
        train_command(args)
    elif args['command'] == 'update':
        update_command(args)
    elif args['command'] == 'test_tweet':
        test_tweet_command(args)
    else:  # This should never be reached
        print('Invalid command')
        exit(1)

    exit()


if __name__ == '__main__':
    main()
