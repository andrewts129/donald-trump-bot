import spacy
import sqlite3
import tweepy
import pickle
import zipfile
import tempfile
import json
import requests
from io import BytesIO
import os
import en_core_web_sm
import logging

logger = logging.getLogger(__name__)

# The number of preceding words that will be used to pick the next word in the Markov chain
NUMBER_OF_WORDS_USED = 2

# The db file that contains all of Trump's tweets
ARCHIVE_FILE_NAME = "TrumpTweets.db"

# Text file that contains all of Trump's speeches
SPEECH_FILE_NAME = "AllTrumpSpeechesCleaned.txt"

# Used for getting the JSON files that contain all of Trump's tweets
TWEET_REPO_BASE_URL = "https://github.com/bpb27/trump_tweet_data_archive/raw/master/condensed_%YEAR%.json.zip"
JSON_BASE_NAME = "condensed_%YEAR%.json"

# Getting access to the Twitter API. Authentication data comes from environmental variables
auth = tweepy.OAuthHandler(consumer_key=os.environ["TW_CONSUMER_KEY"],
                           consumer_secret=os.environ["TW_CONSUMER_SECRET"])
auth.set_access_token(key=os.environ["TW_ACCESS_TOKEN"],
                      secret=os.environ["TW_ACCESS_SECRET"])
api = tweepy.API(auth)


def create_tweet_database():
    """Downloads all of Trump's tweets from a github repo and stores the ones written by him in TrumpTweets.db. This is
    not run as part of main, it only needs to be updated whenever changes to the accepted tweets (as specified in
    should_use_tweet()) are made"""

    data_to_write = []
    years_to_use = list(range(2013, 2018))

    with tempfile.TemporaryDirectory() as temp_dir:
        for year in years_to_use:
            url = TWEET_REPO_BASE_URL.replace("%YEAR%", str(year))

            # Downloads the zipped json and unzips it into the temp directory created above
            zippy = requests.get(url)
            zipped_file = zipfile.ZipFile(BytesIO(zippy.content), "r")
            zipped_file.extractall(temp_dir)
            zipped_file.close()

            # Reads the newly-unzipped json into a list of Javascript-type objects
            with open(temp_dir + "/" + JSON_BASE_NAME.replace("%YEAR%", str(year))) as json_file:
                raw_tweets = json.load(json_file)

            for raw_tweet in raw_tweets:

                # Don't use retweets or tweets that would fail the conditions set by should_use_tweet
                if raw_tweet["is_retweet"] is False and should_use_tweet(raw_tweet["text"], raw_tweet["source"]):
                    data = (raw_tweet["id_str"], raw_tweet["text"], raw_tweet["source"], raw_tweet["created_at"])
                    data_to_write.append(data)

    db = sqlite3.connect(ARCHIVE_FILE_NAME)
    cursor = db.cursor()

    # id is the id of every tweet, as assigned by Twitter
    cursor.execute("CREATE TABLE tweets(id INTEGER PRIMARY KEY, text TEXT, source TEXT, time TEXT)")
    db.commit()

    cursor.executemany("INSERT INTO tweets(id, text, source, time) VALUES(?,?,?,?)", data_to_write)
    db.commit()


def should_use_tweet(text, source):
    """Determines whether a tweet should be used by the bot to construct new tweets

        Args:
            text - the text of the tweet, as a String
            source - the Twitter client the tweet came from, as a String in the form "Twitter for Android"
    """

    # The Sources that seem to contain actual tweets from Trump
    acceptable_sources = ["Twitter for Android", "Twitter for iPad", "Twitter for iPhone", "Twitter Web Client",
                          "Twitter for BlackBerry"]

    # Exclude retweets, his weird manual retweets, and replies
    unacceptable_starts = ["RT", '"@', "@", "'@", "Via"]

    # Trump himself also doesn't use links or hashtags at all. Also get rid of his quotes
    unacceptable_strings = ["t.co", "#", ".ly", ".com", "Thoreau", "Edison", "- Vince", "- Arnold", "Emerson"]

    # Return true if the tweet comes from an acceptable source, doesn't start with something bad, and doesn't
    # have a string that indicates Trump didn't write it
    return source in acceptable_sources \
        and not any(text.startswith(x) for x in unacceptable_starts) \
        and not any((x in text) for x in unacceptable_strings)


def update_tweet_archive(archive_file_path):
    """When called, this will update the SQLite database that contains all of @realDonaldTrump's tweets with all of the
    newer tweets that are not currently in it.

    Args:
        archive_file_path - the name of the .db file that tweets are stored in (created with create_tweet_database())
    """

    def download_new_tweets(newest_id):
        """Downloads all tweets from @realDonaldTrump that are more recent than the one with the given ID"""

        all_tweets = []

        # make initial request for most recent tweets (200 is the maximum allowed count)
        recent_tweets = api.user_timeline(screen_name='@realDonaldTrump', count=200, since_id=newest_id)

        # save most recent tweets
        all_tweets.extend(recent_tweets)

        # save the id of the oldest tweet less one
        oldest_id = all_tweets[-1].id - 1

        # keep grabbing tweets until there are no tweets left to grab
        while len(recent_tweets) > 0:
            # all subsequent requests use the max_id param to prevent duplicates
            recent_tweets = api.user_timeline(screen_name='@realDonaldTrump', count=200, max_id=oldest_id,
                                              since_id=newest_id)
            # save most recent tweets
            all_tweets.extend(recent_tweets)

            # update the id of the oldest tweet less one
            oldest_id = all_tweets[-1].id - 1

        return all_tweets

    db = sqlite3.connect(archive_file_path)
    cursor = db.cursor()

    # Gets the highest tweet ID in the archive
    cursor.execute('SELECT MAX(id) FROM tweets')
    highest_id = cursor.fetchone()[0]

    # If the last tweet in the archive isn't the last thing tweeted, download all new tweets
    last_tweet_id = int(api.user_timeline(screen_name='@realDonaldTrump', count=200)[0].id_str)

    if highest_id < last_tweet_id:

        new_tweets = download_new_tweets(highest_id)

        # Creates a list of tuples containing the data (id, tweet text, and source)
        new_tweets_list = []

        for tweet in new_tweets:
            tweet_id = tweet.id_str
            tweet_text = tweet.text
            tweet_source = tweet.source
            tweet_time = tweet.created_at

            # Makes sure that only tweets that probably actually came from Trump are put into the archive
            if should_use_tweet(tweet_text, tweet_source):
                data = (tweet_id, tweet_text, tweet_source, tweet_time)
                new_tweets_list.append(data)

        # Puts all the tuples into the db file
        cursor.executemany("INSERT INTO tweets(id, text, source, time) VALUES(?,?,?,?)", new_tweets_list)
        db.commit()
        cursor.close()


def get_tweets_as_strings(archive_file_path):
    """Returns the tweets that will be used in building the Markov chain as a list of strings from the .db file created
    in create_tweet_database()"""

    db = sqlite3.connect(archive_file_path)
    cursor = db.cursor()

    cursor.execute("SELECT text, time FROM tweets")

    # The fetchall returns a list of tuples
    list_of_tweets_tuples = cursor.fetchall()
    cursor.close()

    # The list of strings
    list_of_tweets = []

    # Tweets from these years will be added to the list twice so that the markov chain tweets resemble modern Trump
    # more
    weighted_years = list(range(2016, 2021))

    for tweet in list_of_tweets_tuples:
        tweet_text = tweet[0]
        tweet_time = tweet[1]

        list_of_tweets.append(tweet_text)

        if any((str(x) in tweet_time) for x in weighted_years):
            list_of_tweets.append(tweet_text)

    return list_of_tweets


def get_ngrams(sentence, nlp):
    """Returns a list of all the n-grams of NUMBER_OF_WORDS_USED length in the sentence, with each gram consisting of a
    word and its part of speech

    Args:
        sentence - a string of words
        nlp - an loaded instance of Spacy
    """

    list_of_ngrams = []

    tokenized_sentence = nlp(sentence)

    # Loops over the sentence, skipping the first n words because they don't have enough preceding words to create
    # prediction probabilities
    for index, token in enumerate(tokenized_sentence[NUMBER_OF_WORDS_USED:]):

        # Compensate for the string slicing above by moving the index forwards to it's proper place in the original
        index += NUMBER_OF_WORDS_USED

        preceding_words = []

        # Gets the previous n words that will be used as preceding states to determine the next word
        for i in range(index - NUMBER_OF_WORDS_USED, index):
            preceding_token = tokenized_sentence[i]

            # Gets the data we need from the token, the word and it's part of speech
            preceding_token_tuple = (str(preceding_token), preceding_token.pos_)
            preceding_words.append(preceding_token_tuple)

        # Gets the data we need from the token, the word and it's part of speech
        last_word = (str(token), token.pos_)

        # Adds the last word (the one that could be predicted) to the created list and add the result
        # to the master list of n-grams for the sentence
        preceding_words.append(last_word)
        list_of_ngrams.append(preceding_words)

    return list_of_ngrams


def update_frequency(master_frequency_dict, ngrams):
    """Given a tuple of at least two items, update the dictionary to show that the first n-1 words preceded the last
    once more

    Args:
        master_frequency_dict - the dictionary that will be updated
        ngrams - a list of tuples at least 2 long
    """

    preceding_words = tuple(ngrams[:-1])  # Tupled so it can be a dict key
    predicted_word = ngrams[-1]

    master_frequency_dict.setdefault(preceding_words, {})
    master_frequency_dict[preceding_words].setdefault(predicted_word, 0)
    master_frequency_dict[preceding_words][predicted_word] += 1


def should_be_starter(tweet_text):
    """Return true if the first few words of the string should be used as a starting point for building a tweet"""
    return not tweet_text.startswith(".@")


def get_speeches():
    """Loads Trump's speeches as a list of Strings, with each entry being a paragraph"""

    with open(SPEECH_FILE_NAME) as file:
        speeches = file.readlines()

    return speeches


def main():
    update_tweet_archive(ARCHIVE_FILE_NAME)

    # For whatever reason, standard loading methods for spacy don't work on the RPI. This appears to work tho
    nlp = en_core_web_sm.load() 

    word_frequency_bank = {}
    starter_words = []

    tweets = get_tweets_as_strings(ARCHIVE_FILE_NAME)

    for tweet in tweets:
        tweet_ngrams = get_ngrams(tweet, nlp)

        # Gets the first n words of the tweet and stores it as a possible starter for building tweets later
        if should_be_starter(str(tweet)):

            # There's one or two tweets that are only a word long, so this sometimes will throw an IndexError
            try:
                tweet_starter = tweet_ngrams[0][:NUMBER_OF_WORDS_USED]
                starter_words.append(tweet_starter)
            except IndexError:
                pass

        for ngram in tweet_ngrams:
            update_frequency(word_frequency_bank, ngram)

    speeches = get_speeches()

    for speech in speeches:
        # Get rid of the newline char at the end of every line
        speech = speech.replace("\n", "\n")

        speech_ngrams = get_ngrams(speech, nlp)

        # To keep things Twittery, do not use speeches as starter sequences
        for ngram in speech_ngrams:
            update_frequency(word_frequency_bank, ngram)

    with open('wordbank.pkl', 'wb') as file:
        pickle.dump(word_frequency_bank, file)

    with open('starters.pkl', 'wb') as file:
        pickle.dump(starter_words, file)

    print('done')


if __name__ == "__main__":
    main()
