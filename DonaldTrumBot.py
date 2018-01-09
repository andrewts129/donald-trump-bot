import random
import tweepy
from numpy.random import choice
import pickle
import requests
import configparser
import re
import os

# Getting settings that are shared between this script and the word bank building script
shared_configs = configparser.ConfigParser()
shared_configs.read("Config.ini")

# The number of preceding words that will be used to pick the next word in the Markov chain
NUMBER_OF_WORDS_USED = int(shared_configs["Configuration"]["NUMBER_OF_WORDS_USED"])

# Minutes between script runs
WAKE_UP_INTERVAL = 10

# The average number of times that the bot should tweet per day
AVG_TIMES_TO_TWEET_PER_DAY = 2.5

# Max number of chars in a generated tweet. Should be <= Max number of chars allowed by Twitter
MAX_TWEET_LENGTH = 200

# Getting access to the Twitter API. Authentication data comes from environmental variables
auth = tweepy.OAuthHandler(consumer_key=os.environ["TW_CONSUMER_KEY"],
                           consumer_secret=os.environ["TW_CONSUMER_SECRET"])
auth.set_access_token(key=os.environ["TW_ACCESS_TOKEN"],
                      secret=os.environ["TW_ACCESS_SECRET"])
api = tweepy.API(auth)


def get_starter_letters():
    """Downloads a list of the start of Trump's tweets that will be used as the starting seed of the Markov chain"""

    url = "https://drive.google.com/uc?id=0B8xDokak7DY3S3p0RUppZUNRTWs"     # My Google Drive
    starter_pickle = requests.get(url).content
    print("Downloaded starter words...")
    all_starters = pickle.loads(starter_pickle)

    return all_starters


def get_word_bank():
    """Downloads the word bank containing all the words (and their part of speech), as well as the two words that
    precede them"""

    url = "https://drive.google.com/uc?id=0B8xDokak7DY3OGxuLVo5d1loZTA"     # My Google Drive
    word_bank_pickle = requests.get(url).content
    print("Downloaded word bank...")
    word_bank = pickle.loads(word_bank_pickle)

    return word_bank


def get_tweets_to_reply_to():
    """Gets a list of tweets that are directed towards @DonaldTrumBot and returns a list of those tweets that it has
        not liked (do not reply to tweets that have been liked by @DonaldTrumBot)"""

    def get_tweets_bot_liked_ids():
        """Gets the ids of every tweet that the authenticated user has liked. NOTE: This might only retrieve the latest
        n tweets. Doesn't really matter for now though"""
        list_of_ids = []

        for favorited_tweet in tweepy.Cursor(api.favorites).items():
            list_of_ids.append(favorited_tweet.id)

        return list_of_ids

    # Gets the tweets that are directed at TrumBot
    replies_to_me = api.search('@DonaldTrumBot')

    # Adds all non-retweets to a list
    replies_to_reply_to = []

    my_liked_tweet_ids = get_tweets_bot_liked_ids()

    for reply in replies_to_me:
        if not hasattr(reply, 'retweeted_status') and reply.id not in my_liked_tweet_ids:
            replies_to_reply_to.append(reply)

    return replies_to_reply_to


def should_tweet_now():
    """Will return true enough so that the bot tweets AVG_TIMES_TO_TWEET_PER_DAY per day, so long as this script
    is run every WAKE_UP_INTERVAL minutes"""
    wakeups_per_day = (24 * 60) / WAKE_UP_INTERVAL

    chance_to_tweet = AVG_TIMES_TO_TWEET_PER_DAY / wakeups_per_day

    return chance_to_tweet > random.random()


def create_tweet(starter_words, word_frequencies):

    def chain_to_string(chain_list):
        """When given a list of (word, part_of_speech) tuples, clean it up and convert it into a string"""

        out_string = ""

        for item in chain_list:
            # The first chunk of each tuple is the word (second part is the part of speech)
            out_string = out_string + item[0] + ' '

        # Lots of little minor adjustments that make the output text look a little more natural

        # Ensures that punctuation characters are consistent
        # This needs to come before the next block because that one assumes that there's no fancy punctuation
        out_string = out_string.replace("’", "'")
        out_string = out_string.replace('“', '"')
        out_string = out_string.replace('”', '"')

        out_string = out_string.replace(" !", "!")
        out_string = out_string.replace(" .", ".")
        out_string = out_string.replace(" ?", "?")
        out_string = out_string.replace("# ", "#")
        out_string = out_string.replace("$ ", "$")
        out_string = out_string.replace("( ", "(")
        out_string = out_string.replace(" )", ")")
        out_string = out_string.replace(" ,", ",")
        out_string = out_string.replace(" ;", ";")
        out_string = out_string.replace(" '", "'")
        out_string = out_string.replace(" n'", "n'")
        out_string = out_string.replace(" :", ":")
        out_string = out_string.replace(" %", "%")
        out_string = out_string.replace(" - ", "-")
        out_string = out_string.replace("   ", " ")
        out_string = out_string.replace("  ", " ")
        out_string = out_string.replace("&amp;", "&")
        out_string = out_string.replace("\n", "")
        out_string = out_string.replace(" …", "…")

        # Removes parentheses if there aren't two of them
        if "(" not in out_string or ")" not in out_string:
            out_string = out_string.replace("(", "")
            out_string = out_string.replace(")", "")

        # Remove quotes if there is an odd number as that means there is a mismatch (and I can't be bothered to figure
        # out how to match them right now)
        if out_string.count('"') % 2 is not 0:
            out_string = out_string.replace('"', "")

        out_string = out_string.strip()

        return out_string

    def create_p_values(numbers):
        """When given a list of numbers, adjusts it so that all the numbers add up to 1 (but keep the same ratios
        between them)"""

        total_sum = sum(numbers)

        output = []

        for number in numbers:
            p = float(number) / total_sum
            output.append(p)

        return output

    def get_next_word(word_freqs, last_n_tuples):

        # The last n letters of the tweet
        key_to_lookup = tuple(last_n_tuples)

        if key_to_lookup in word_freqs.keys():
            possible_next_words = list(word_freqs[key_to_lookup].keys())
            possible_next_word_probabilities = list(word_freqs[key_to_lookup].values())
            possible_next_word_probabilities = create_p_values(possible_next_word_probabilities)

            # numpy.choice doesn't like tuples, so we need to use indicies to select instead of just picking
            # the value
            return possible_next_words[choice(len(possible_next_words), p=possible_next_word_probabilities)]

        else:
            return None

    def cut_to_tweet_size(string):

        if len(string) <= MAX_TWEET_LENGTH:
            return string
        else:
            sentences = re.split("([!.?…])", string)

            result = ""

            for sentence in sentences:
                if len(result + sentence) > MAX_TWEET_LENGTH:
                    return result
                else:
                    result += sentence

    # Pick a random start-of-tweet to begin constructing the Markov chain
    tweet_chain = random.choice(starter_words)
    tweet_string = chain_to_string(tweet_chain)

    # Generate a Markov chain that is probably longer than what we can use (this will probably end early because the
    # chain will reach a dead-end though)
    while len(tweet_string) < MAX_TWEET_LENGTH * 5:
        next_word = get_next_word(word_frequencies, tweet_chain[-NUMBER_OF_WORDS_USED:])

        if next_word is None:
            break
        else:
            tweet_chain.append(next_word)
            tweet_string = chain_to_string(tweet_chain)

    tweet_string = cut_to_tweet_size(tweet_string)

    # If there's no way to make the string under MAX_TWEET_LENGTH chars, just try again
    if len(tweet_string) == 0:
        tweet_string = create_tweet(starter_words, word_frequencies)

    return tweet_string


def post_tweet(tweet_string, status_id_to_reply_to=None):
    if status_id_to_reply_to is None:
        api.update_status(tweet_string)
    else:
        user_to_reply_to = api.get_status(status_id_to_reply_to).author.screen_name
        api.update_status("@" + user_to_reply_to + " " + tweet_string, status_id_to_reply_to)


def main():

    print("Waking up...")

    tweets_to_reply_to = get_tweets_to_reply_to()
    should_make_tweet_now = should_tweet_now()

    if len(tweets_to_reply_to) > 0 or should_make_tweet_now:

        # Gets the word data needed to build the tweets
        tweet_starter_words = get_starter_letters()
        tweet_word_frequencies = get_word_bank()

        for reply in tweets_to_reply_to:
            string_to_tweet = create_tweet(tweet_starter_words, tweet_word_frequencies)

            print("Replying to Tweet " + str(reply.id) + " with: " + string_to_tweet)
            post_tweet(string_to_tweet, status_id_to_reply_to=reply.id)
            api.create_favorite(reply.id)

        if should_make_tweet_now:
            print("Going to tweet...")
            string_to_tweet = create_tweet(tweet_starter_words, tweet_word_frequencies)

            print("Tweeting: " + string_to_tweet)
            post_tweet(string_to_tweet)

    else:
        print("Not tweeting...")


if __name__ == "__main__":
    main()
