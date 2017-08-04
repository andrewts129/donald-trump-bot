import spacy
import sqlite3
import tweepy
import pickle
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import configparser

# Getting settings that are shared between this script and the tweeting script
shared_configs = configparser.ConfigParser()
shared_configs.read("Config.ini")

# The number of preceding words that will be used to pick the next word in the Markov chain
NUMBER_OF_WORDS_USED = int(shared_configs["Configuration"]["NUMBER_OF_WORDS_USED"])

# The db file that contains all of Trump's tweets
ARCHIVE_FILE_NAME = "TrumpTweets.db"

# Text file that contains all of Trump's speeches
SPEECH_FILE_NAME = "AllTrumpSpeechesCleaned.txt"

# Getting access to the Twitter API. Authentication data comes from TwitterKeys.ini
api_keys_config = configparser.ConfigParser()
api_keys_config.read("TwitterKeys.ini")
auth = tweepy.OAuthHandler(consumer_key=api_keys_config["TwitterAuth"]["CONSUMER_KEY"],
                           consumer_secret=api_keys_config["TwitterAuth"]["CONSUMER_SECRET"])
auth.set_access_token(key=api_keys_config["TwitterAuth"]["ACCESS_TOKEN"],
                      secret=api_keys_config["TwitterAuth"]["ACCESS_SECRET"])
api = tweepy.API(auth)


# TODO Make sure that the archive only contains tweets that we should use

# When called, this will update the SQLite database that contains all of @realDonaldTrump's tweets with all of the
# newer tweets that are not currently in it.
def update_tweet_archive(archive_file_path):
    # Downloads all tweets that are more recent than the one with the given ID
    def download_new_tweets(newest_id):
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

    # TODO
    def should_use_tweet(text, source):

        # The Sources that seem to contain actual tweets from Trump
        acceptable_sources = ["Twitter for Android", "Twitter for iPad", "Twitter for iPhone", "Twitter Web Client"]

        # Exclude retweets, his weird manual retweets, and replies
        unacceptable_starts = ["RT", '"@', "@"]

        # Trump himself also doesn't use links or hashtags at all
        unacceptable_strings = ["t.co", "#"]

        # Return true if the tweet comes from an acceptable source, doesn't start with something bad, and doesn't
        # have a string that indicates Trump didn't write it
        return source in acceptable_sources \
            and not any(text.startswith(x) for x in unacceptable_starts) \
            and not any((x in text) for x in unacceptable_strings)

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

            # Makes sure that only tweets that probably actually came from Trump are put into the archive
            if should_use_tweet(tweet_text, tweet_source):
                data = (tweet_id, tweet_text, tweet_source)
                new_tweets_list.append(data)

        # Puts all the tuples into the db file
        cursor.executemany('INSERT INTO tweets(id, text, source) VALUES(?,?,?)', new_tweets_list)
        db.commit()
        cursor.close()


# Returns the tweets that will be used in building the Markov chain as a list of strings
def get_tweets_as_strings(archive_file_path):
    db = sqlite3.connect(archive_file_path)
    cursor = db.cursor()

    cursor.execute('SELECT text FROM tweets')

    # The fetchall returns a list of tuples with one value each, we need them to be strings
    list_of_tweets_tuples = cursor.fetchall()
    cursor.close()

    # The list of strings
    list_of_tweets = []

    for tweet in list_of_tweets_tuples:
        list_of_tweets.append(tweet[0])

    return list_of_tweets


# Returns a list of all the n-grams of NUMBER_OF_WORDS_USED length in the sentence, with each gram
# consisting of a word and its part of speech
def get_ngrams(sentence, nlp):
    # TODO Better variable name
    list_of_ngrams = []

    tokenized_sentence = nlp(sentence)

    # TODO Explain this better
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


# TODO
def update_frequency(master_frequency_dict, ngrams):
    preceding_words = tuple(ngrams[:-1])  # Tupled so it can be a dict key
    predicted_word = ngrams[-1]

    master_frequency_dict.setdefault(preceding_words, {})
    master_frequency_dict[preceding_words].setdefault(predicted_word, 0)
    master_frequency_dict[preceding_words][predicted_word] += 1


# TODO
def should_be_starter(tweet_text):
    return not tweet_text.startswith(".@")


# TODO
def get_speeches():
    with open(SPEECH_FILE_NAME) as file:
        speeches = file.readlines()

    return speeches


def upload(word_freqs, starters):

    with open('wordbank.pkl', 'wb') as file:
        pickle.dump(word_freqs, file)

    with open('starters.pkl', 'wb') as file:
        pickle.dump(starters, file)

    googleAuth = GoogleAuth()
    googleAuth.LocalWebserverAuth()
    drive = GoogleDrive(googleAuth)

    for file in drive.ListFile().GetList():
        print(file['title'])
        if file['title'] == 'wordbank.pkl':
            file.SetContentFile('wordbank.pkl')
            file.Upload()

        elif file['title'] == 'starters.pkl':
            file.SetContentFile('starters.pkl')
            file.Upload()


def main():
    update_tweet_archive(ARCHIVE_FILE_NAME)

    nlp = spacy.load("en")

    word_frequency_bank = {}
    starter_words = []

    tweets = get_tweets_as_strings(ARCHIVE_FILE_NAME)

    for tweet in tweets:
        tweet_ngrams = get_ngrams(tweet, nlp)

        # Gets the first n words of the tweet and stores it as a possible starter for building tweets later
        if should_be_starter(str(tweet)):
            tweet_starter = tweet_ngrams[0][:-1]
            starter_words.append(tweet_starter)

        for ngram in tweet_ngrams:
            update_frequency(word_frequency_bank, ngram)

    speeches = get_speeches()

    for speech in speeches:
        speech_ngrams = get_ngrams(speech, nlp)

        # To keep things Twittery, do not use speeches as starter sequences

        for ngram in speech_ngrams:
            update_frequency(word_frequency_bank, ngram)

    upload(word_frequency_bank, starter_words)

    print('done')

if __name__ == "__main__":
    main()
