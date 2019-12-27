import itertools
import multiprocessing as mp
import random
from collections import defaultdict
from functools import partial
from typing import List, NamedTuple, Iterable, Dict, Optional, Tuple

import ndjson
import nltk
from nltk.tokenize.casual import TweetTokenizer
from numpy.random import beta

from utils.TweetValidator import should_use_tweet
from namedtuples.Token import Token
from namedtuples.Tweet import Tweet, tweet_json_decode_hook

_NGram = Tuple[Token, ...]


class _TokenProbability(NamedTuple):
    token: Token
    probability: float


class _Weights:
    def __init__(self, n_plus_one_grams: Iterable[_NGram] = None):
        # Using partial(defaultdict, int) instead of standard defaultdict(lambda: int) bc the latter cannot be pickled
        self._conditional_counts: Dict[_NGram, Dict[Token, int]] = defaultdict(partial(defaultdict, int))

        if n_plus_one_grams is not None:
            for n_plus_one_gram in n_plus_one_grams:
                self.add(n_plus_one_gram[:-1], n_plus_one_gram[-1])

    def add(self, ngram: _NGram, next_token: Token) -> None:
        self._conditional_counts[ngram][next_token] += 1

    def get_ml_estimates(self, ngram: _NGram) -> List[_TokenProbability]:
        # Get maximum likelihood estimates for each token that might succeed the given ngram
        # TODO use MAP instead
        total_count = sum(self._conditional_counts[ngram].values())
        return [_TokenProbability(token, count / total_count) for token, count in self._conditional_counts[ngram].items()]

    def clear(self) -> None:
        self._conditional_counts.clear()


class Model:
    def __init__(self, tweets: Iterable[Tweet] = None, n: int = 2):
        self._n = n
        self._tokenizer = TweetTokenizer()

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

        n_plus_one_grammed_tweets = (Model._to_ngrams(tweet, self._n + 1) for tweet in tokenized_tweets)
        for n_plus_one_gram in itertools.chain(*n_plus_one_grammed_tweets):  # Flattens the nested lists
            ngram = n_plus_one_gram[:-1]
            next_token = n_plus_one_gram[-1]
            self._weights.add(ngram, next_token)

    def get_seed(self) -> List[Token]:
        random_ngram = random.choice(self._seeds)
        return list(random_ngram)

    def predict_next_token(self, tokens: List[Token]) -> Optional[Token]:
        last_ngram = tuple(tokens[-self._n:])

        successors = self._weights.get_ml_estimates(last_ngram)
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
        self._seeds.extend([Model._to_ngrams(tweet, self._n)[0] for tweet in tokenized_tweets if len(tweet) > self._n])

    @staticmethod
    def _to_ngrams(tokens: Iterable[Token], n: int) -> List[_NGram]:
        return list(nltk.ngrams(tokens, n))

    def _preprocess_tweets(self, tweets: Iterable[Tweet]) -> List[List[Token]]:
        tweet_texts = (tweet.text for tweet in tweets)

        with mp.Pool() as pool:
            tokenized_tweets = pool.map(self._tokenizer.tokenize, tweet_texts)
            pos_tagged_tokenized_tweets = pool.map(nltk.pos_tag, tokenized_tweets)

        # Converts the word-pos tuples returned by nltk.pos_tag() to Token objects
        return [[Token(*token) for token in tweet] for tweet in pos_tagged_tokenized_tweets]


class LazyFitModel(Model):
    def __init__(self, tweets: Iterable[Tweet] = None, n: int = 2):
        self._tokenized_tweets = None
        super().__init__(tweets, n)

    def fit(self, tweets: Iterable[Tweet]) -> None:
        self._tokenized_tweets = []
        super().fit(tweets)

    def partial_fit(self, tweets: Iterable[Tweet]) -> None:
        self._tokenized_tweets = self._preprocess_tweets(tweets)
        self._set_seeds(self._tokenized_tweets)

        if self._weights is None:
            self._weights = _Weights()

    def predict_next_token(self, tokens: List[Token]) -> Optional[Token]:
        last_n_tokens = tokens[-self._n:]
        relevant_tweets = (tweet for tweet in self._tokenized_tweets if all((token in tweet) for token in last_n_tokens))

        for tweet in relevant_tweets:
            for n_plus_one_gram in Model._to_ngrams(tweet, self._n + 1):
                ngram = n_plus_one_gram[:-1]
                next_token = n_plus_one_gram[-1]
                self._weights.add(ngram, next_token)

        prediction = super().predict_next_token(tokens)
        self._weights.clear()
        return prediction


def train_model_from_file(tweets_ndjson_filename: str, n: int = 2, lazy_fitting: bool = False) -> Model:
    with open(tweets_ndjson_filename, 'r') as fp:
        tweets = ndjson.load(fp, object_hook=tweet_json_decode_hook)

    tweets = (tweet for tweet in tweets if should_use_tweet(tweet))

    if lazy_fitting:
        model = LazyFitModel(tweets, n)
    else:
        model = Model(tweets, n)

    return model
