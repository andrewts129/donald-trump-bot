from typing import Iterable

import nltk

from utils.Model import Model
from namedtuples.Token import Token


def _fix_quotes(s: str) -> str:
    first_quote_index = s.find('"')
    second_quote_index = s.find('"', first_quote_index + 1)

    # If there was only one quote
    if second_quote_index == -1:
        return s.replace(' " ', ' ')
    else:
        head = s[:second_quote_index + 2]  # Get the whitespace after it too
        fixed_head = head.replace(' " ', ' "', 1).replace(' " ', '" ', 1)

        tail = s[second_quote_index + 2:]
        fixed_tail = _fix_quotes(tail)

        return f'{fixed_head}{fixed_tail}'


def _fix_parenthesis(s: str) -> str:
    first_opener_index = s.find('(')
    first_closer_index = s.find(')')

    if first_opener_index == -1:
        return s.replace(')', ' ')
    elif first_closer_index == -1:
        return s.replace('(', ' ')
    else:
        up_to_first_opener = s[:first_opener_index].strip()
        between_parenthesis = s[first_opener_index + 1:first_closer_index].strip()
        after_first_closer = s[first_closer_index + 1:].strip()

        return f'{up_to_first_opener} ({_fix_parenthesis(between_parenthesis)}) {_fix_parenthesis(after_first_closer)}'


def _join_tokens(tokens: Iterable[Token]) -> str:
    output = ' '.join(token.word for token in tokens)

    # TODO regex replacement for two-letter acronyms
    replacements = [
        (' ,', ','), (' .', '.'), (' ?', '?'), (' !', '!'), (' :', ':'), (' ;', ';'), ('... ', '...'), (' …', '…'),
        ('. @', '.@'), ('- -', '--'), ('U. S.', 'U.S.'), ('A. G.', 'A.G.'), ('D. C.', 'D.C.'), ('T. V.', 'T.V.'),
        ('P. M.', 'P.M.'), ('A. M.', 'A.M.'), ('0, 0', '0,0'), ('$ ', '$'), (' %', '%'), ('MS - 13', 'MS-13'),
        ('# ', '#'), ('w /', 'w/'), (' / ', '/'), ('“', '"'), ('”', '"'), ('’', "'"), ("n ' t", "n't"),
        (" ' s", "'s"), (" ' v", "'v"), (" ' m", "'m"), (" ' re", "'re"), ("' 0", "'0"), (" ' ", ' " ')
    ]
    for replacement_pair in replacements:  # Order does matter
        output = output.replace(*replacement_pair)

    output = _fix_quotes(output)
    output = _fix_parenthesis(output)
    output = output.replace('   ', ' ')  # The above methods sometimes introduce extra spaces
    output = output.replace('  ', ' ')

    return output.strip()


def _prune_tweet(tweet: str, max_length: int) -> str:
    sentences = nltk.tokenize.sent_tokenize(tweet)

    result = ''
    for sentence in sentences:
        result_after_appending = f'{result} {sentence}'
        if len(result_after_appending) > max_length:
            break
        else:
            result = result_after_appending

    return result.strip()


def create_tweet(model: Model, max_length: int) -> str:
    tweet = ''

    # Keep trying in case the entire thing gets pruned
    while len(tweet) < 5:  # 5 is arbitrary
        tokens_to_generate = max_length // 3  # 3 is also somewhat arbitrary
        tokens = model.generate_tokens(tokens_to_generate)
        too_long_tweet = _join_tokens(tokens)
        tweet = _prune_tweet(too_long_tweet, max_length)

    return tweet
