from typing import Iterable

import nltk

from Model import Model
from namedtuples.Token import Token


def _join_tokens(tokens: Iterable[Token]) -> str:
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


def _prune_tweet(tweet: str, max_length: int) -> str:
    sentences = nltk.tokenize.sent_tokenize(tweet)

    result = ''
    for sentence in sentences:
        result_after_appending = f'{result} {sentence}'
        if len(result) > max_length:
            break
        else:
            result = result_after_appending

    return result.strip()


def create_tweet(model: Model, max_length: int) -> str:
    tokens_to_generate = max_length // 3  # Somewhat arbitrary
    tokens = model.generate_tokens(tokens_to_generate)
    too_long_tweet = _join_tokens(tokens)
    return _prune_tweet(too_long_tweet, max_length)
