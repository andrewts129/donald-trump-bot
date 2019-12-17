import itertools
import multiprocessing as mp
import random
from collections import defaultdict
from functools import partial
from typing import List, NamedTuple, Iterable, Dict, Optional

import ndjson
import nltk
from nltk.tokenize.casual import TweetTokenizer
from numpy.random import beta

from TweetValidator import should_use_tweet
from namedtuples.Token import Token
from namedtuples.Tweet import Tweet, tweet_json_decode_hook


class _Bigram(NamedTuple):
    first: Token
    second: Token


class _Trigram(NamedTuple):
    first: Token
    second: Token
    third: Token


class _TokenProbability(NamedTuple):
    token: Token
    probability: float


class _Weights:
    def __init__(self, trigrams: Iterable[_Trigram] = None):
        # Using partial(defaultdict, int) instead of standard defaultdict(lambda: int) bc the latter cannot be pickled
        self._counts: Dict[_Bigram, Dict[Token, int]] = defaultdict(partial(defaultdict, int))

        if trigrams is not None:
            for trigram in trigrams:
                self.add(trigram)

    def add(self, trigram: _Trigram) -> None:
        beginning_bigram = _Bigram(trigram.first, trigram.second)
        last_token = trigram.third
        self._counts[beginning_bigram][last_token] += 1

    def get_successor_probabilities(self, bigram: _Bigram) -> List[_TokenProbability]:
        total_count = sum(self._counts[bigram].values())
        return [_TokenProbability(pair[0], pair[1] / total_count) for pair in self._counts[bigram].items()]


class Model:
    def __init__(self, tweets: Iterable[Tweet] = None):
        self._tokenizer = TweetTokenizer()
        self._seeds = []
        self._weights = _Weights()

        if tweets is not None:
            self.fit(tweets)

    def fit(self, tweets: Iterable[Tweet]) -> None:
        tokenized_tweets = self._preprocess_tweets(tweets)

        # Get the first bigram from each tweet
        self._seeds = [Model._to_bigrams(tweet)[0] for tweet in tokenized_tweets if len(tweet) > 2]

        trigrammed_tweets = (Model._to_trigrams(tweet) for tweet in tokenized_tweets)
        for trigram in itertools.chain(*trigrammed_tweets):  # Flattens the nested lists
            self._weights.add(trigram)

    def get_seed(self) -> List[Token]:
        random_bigram = random.choice(self._seeds)
        return [random_bigram.first, random_bigram.second]

    def predict_next_token(self, tokens: List[Token]) -> Optional[Token]:
        last_bigram = _Bigram(tokens[-2], tokens[-1])

        successors = self._weights.get_successor_probabilities(last_bigram)
        successors = list(sorted(successors, key=lambda sp: sp.probability))

        if len(successors) > 0:
            successor_tokens, probabilities = zip(*successors)
            cumulative_probabilities = [prob + sum(probabilities[:i]) for i, prob in enumerate(probabilities)]

            random_num = beta(3, 1)  # Skews towards higher numbers. Increases bias towards common patterns
            chosen_index = next(i for i, prob in enumerate(cumulative_probabilities) if random_num <= prob)

            return successor_tokens[chosen_index]
        else:
            return None

    def generate_tokens(self, n: int) -> List[Token]:
        chain = self.get_seed()
        while len(chain) < n:
            next_token = self.predict_next_token(chain)
            if next_token is not None:
                chain.append(next_token)
            else:
                break

        return chain

    @staticmethod
    def _to_bigrams(tokens: Iterable[Token]) -> List[_Bigram]:
        return [_Bigram(*gram) for gram in nltk.ngrams(tokens, 2)]

    @staticmethod
    def _to_trigrams(tokens: Iterable[Token]) -> List[_Trigram]:
        return [_Trigram(*gram) for gram in nltk.ngrams(tokens, 3)]

    def _preprocess_tweets(self, tweets: Iterable[Tweet]) -> List[List[Token]]:
        tweet_texts = (tweet.text for tweet in tweets)

        with mp.Pool() as pool:
            tokenized_tweets = pool.map(self._tokenizer.tokenize, tweet_texts)
            pos_tagged_tokenized_tweets = pool.map(nltk.pos_tag, tokenized_tweets)

        # Converts the word-pos tuples returned by nltk.pos_tag() to Token objects
        return [[Token(*token) for token in tweet] for tweet in pos_tagged_tokenized_tweets]


def train_model_from_file(tweets_ndjson_filename: str) -> Model:
    with open(tweets_ndjson_filename, 'r') as f:
        tweets = ndjson.load(f, object_hook=tweet_json_decode_hook)

    tweets = (tweet for tweet in tweets if should_use_tweet(tweet))

    model = Model(tweets)
    return model
