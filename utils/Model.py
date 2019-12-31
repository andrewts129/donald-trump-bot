import itertools
import multiprocessing as mp
import random
from collections import defaultdict
from functools import partial
from typing import List, NamedTuple, Iterable, Dict, Optional, Tuple

import ndjson
import nltk
from nltk.tokenize import word_tokenize
from numpy.random import beta

from namedtuples.Token import Token
from namedtuples.Tweet import Tweet, tweet_json_decode_hook
from utils.TweetValidator import should_use_tweet

_NGram = Tuple[Token, ...]


class _TokenProbability(NamedTuple):
    token: Token
    probability: float


class _Weights:
    # TODO experiment with storing tokens/ngrams as ints to save memory
    def __init__(self, n_plus_one_grams: Iterable[_NGram] = None):
        # Using partial(defaultdict, int) instead of standard defaultdict(lambda: int) bc the latter cannot be pickled
        self._counts: Dict[_NGram, Dict[Token, int]] = defaultdict(partial(defaultdict, int))

        if n_plus_one_grams is not None:
            for n_plus_one_gram in n_plus_one_grams:
                self.add(n_plus_one_gram[:-1], n_plus_one_gram[-1])

    def add(self, ngram: _NGram, next_token: Token) -> None:
        self._counts[ngram][next_token] += 1

    def enough_data_for_prediction(self, ngram: _NGram) -> bool:
        # Returns True if we can predict without just copying a single existing tweet
        num_possible_successors = len(self._counts[ngram].keys())
        total_occurences = sum(self._counts[ngram].values())
        return num_possible_successors > 1 or total_occurences > 2

    def get_successor_probabilities(self, ngram: _NGram) -> List[_TokenProbability]:
        total_count = sum(self._counts[ngram].values())
        return [_TokenProbability(pair[0], pair[1] / total_count) for pair in self._counts[ngram].items()]

    def clear(self) -> None:
        self._counts.clear()


class Model:
    def __init__(self, min_n: int, max_n: int, tweets: Iterable[Tweet] = None):
        self._min_n = min_n
        self._max_n = max_n

        # Initialized when model is fit
        self._seeds: Optional[List[_NGram]] = None
        self._weights: Optional[_Weights] = None

        if tweets is not None:
            self.fit(tweets)

    def fit(self, tweets: Iterable[Tweet]) -> None:
        self._seeds = []
        self._weights = _Weights()

        self.partial_fit(tweets)

    def partial_fit(self, tweets: Iterable[Tweet]) -> None:
        tokenized_tweets = self._preprocess_tweets(tweets)
        self._set_seeds(tokenized_tweets)

        if self._weights is None:
            self._weights = _Weights()

        for n in range(self._min_n, self._max_n + 1):
            n_plus_one_grammed_tweets = (Model._to_ngrams(tweet, n + 1) for tweet in tokenized_tweets)
            for n_plus_one_gram in itertools.chain(*n_plus_one_grammed_tweets):  # Flattens the nested lists
                ngram = n_plus_one_gram[:-1]
                next_token = n_plus_one_gram[-1]
                self._weights.add(ngram, next_token)

    def get_seed(self) -> List[Token]:
        random_ngram = random.choice(self._seeds)
        return list(random_ngram)

    def predict_next_token(self, tokens: List[Token]) -> Optional[Token]:
        for n in reversed(range(self._min_n, self._max_n + 1)):
            last_ngram = tuple(tokens[-n:])

            if self._weights.enough_data_for_prediction(last_ngram) or n == self._min_n:
                successors = self._weights.get_successor_probabilities(last_ngram)
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

    def _set_seeds(self, tokenized_tweets: Iterable[List[Token]]) -> None:
        if self._seeds is None:
            self._seeds = []

        # Get the first ngram from each tweet
        long_enough_tweets = (tweet for tweet in tokenized_tweets if len(tweet) > self._min_n)
        first_ngrams = (Model._to_ngrams(tweet, self._min_n)[0] for tweet in long_enough_tweets)

        self._seeds.extend(first_ngrams)

    @staticmethod
    def _to_ngrams(tokens: Iterable[Token], n: int) -> List[_NGram]:
        return list(nltk.ngrams(tokens, n))

    @staticmethod
    def _preprocess_tweets(tweets: Iterable[Tweet]) -> List[List[Token]]:
        tweet_texts = (tweet.text for tweet in tweets)

        with mp.Pool() as pool:
            tokenized_tweets = pool.map(word_tokenize, tweet_texts)
            pos_tagged_tokenized_tweets = pool.map(nltk.pos_tag, tokenized_tweets)

        # Converts the word-pos tuples returned by nltk.pos_tag() to Token objects
        return [[Token(*token) for token in tweet] for tweet in pos_tagged_tokenized_tweets]


class LazyFitModel(Model):
    def __init__(self, min_n: int, max_n: int, tweets: Iterable[Tweet] = None):
        self._tokenized_tweets = None
        super().__init__(min_n, max_n, tweets)

    def fit(self, tweets: Iterable[Tweet]) -> None:
        self._tokenized_tweets = []
        super().fit(tweets)

    def partial_fit(self, tweets: Iterable[Tweet]) -> None:
        self._tokenized_tweets = self._preprocess_tweets(tweets)
        self._set_seeds(self._tokenized_tweets)

        if self._weights is None:
            self._weights = _Weights()

    def predict_next_token(self, tokens: List[Token]) -> Optional[Token]:
        for n in range(self._min_n, self._max_n + 1):
            # TODO only train the model on the n needed (aka avoid parsing the n=1 level unless necessary b/c it's big)
            last_n_tokens = tokens[-n:]
            relevant_tweets = (tweet for tweet in self._tokenized_tweets if
                               all((token in tweet) for token in last_n_tokens))

            for tweet in relevant_tweets:
                for n_plus_one_gram in Model._to_ngrams(tweet, n + 1):
                    ngram = n_plus_one_gram[:-1]
                    next_token = n_plus_one_gram[-1]
                    self._weights.add(ngram, next_token)

        prediction = super().predict_next_token(tokens)
        self._weights.clear()
        return prediction


def train_model_from_file(tweets_ndjson_filename: str, min_n: int, max_n: int, lazy_fitting: bool) -> Model:
    with open(tweets_ndjson_filename, 'r') as fp:
        tweets = ndjson.load(fp, object_hook=tweet_json_decode_hook)

    tweets = (tweet for tweet in tweets if should_use_tweet(tweet))

    if lazy_fitting:
        model = LazyFitModel(min_n, max_n, tweets)
    else:
        model = Model(min_n, max_n, tweets)

    return model
