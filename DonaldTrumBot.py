#!/usr/bin/env python3
import pickle
import sys
from typing import Iterable
from timeit import default_timer as timer

from TweetDownloader import dump_all_tweets
from Model import train_model_from_file
from namedtuples.Token import Token


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


def tweet_command() -> None:
    pass


def train_command() -> None:
    # TODO make these configurable
    input_file = 'data/trump_tweets.ndjson'
    output_file = 'model.pkl'

    model = train_model_from_file(input_file)
    with open(output_file, 'wb') as f:
        pickle.dump(model, f)


def update_command() -> None:
    output_file = 'data/trump_tweets.ndjson'  # TODO configurable
    dump_all_tweets(output_file)


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
        chain = model.generate_tokens(100)
        tweets.append(join_tokens(chain))
    tweet_time_total = timer() - tweet_time_start

    print(f'Model training time: {train_time_total:.2f}s')
    print(f'Tweet building time: {tweet_time_total:.2f}s')
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
            exit_status = 2  # TODO
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
