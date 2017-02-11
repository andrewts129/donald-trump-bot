#!/usr/bin/env python

import spacy
import sqlite3
import tweepy
import pickle
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

auth = tweepy.OAuthHandler(consumer_key='F5kphzVfDT5Y5taE467x8dDzX',
                           consumer_secret='5dleu5PeeQ8RXziaOflaXA6jVmGScZNpMvQ7qdrXF29z8l7UbQ')
auth.set_access_token(key='797971904258772996-42sBRXzXu6o4o7lquisdw3RsZ3uoJ3l',
                      secret='RzeKkSzzd5kbzrr0NOu2z3J6E5AULCO6xVUuVVyx9r2NC')
api = tweepy.API(auth)

nlp = spacy.load('en')

existing_word_pos = {}


class WordAndPos(object):
    def __init__(self, word, pos):
        self.word = word
        self.pos_ = pos

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash((self.word, self.pos_))


class Source(object):
    # Handles the source of tweets that are used to construct the Markov chain

    def __init__(self, archive, n):
        def update_archive():
            # Updates the db file with all the tweets that are not in it yet

            def download_new_tweets(newest_id):
                # Downloads all tweets that are more recent than the one with the given ID

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

            # Gets the highest tweet ID in the archive
            cursor.execute('SELECT MAX(id) FROM tweets')
            highest_id = cursor.fetchone()[0]

            # If the last tweet in the archive isn't the last thing tweeted, download all new tweets
            last_tweet_id = int(api.user_timeline(screen_name='@realDonaldTrump', count=200)[0].id_str)

            if highest_id < last_tweet_id:

                new_tweets = download_new_tweets(highest_id)

                # Creates a list of tuples containing the data (id, tweet text, and time)
                new_tweets_list = []

                for tweet in new_tweets:
                    tweet_id = tweet.id_str
                    text = tweet.text
                    tweet_time = tweet.created_at

                    # Makes sure that not retweets make it into the archive.
                    if 'RT @' not in text and '"@' not in text:
                        data = (tweet_id, text, tweet_time)
                        new_tweets_list.append(data)

                # Puts all the tuples into the db file
                cursor.executemany('INSERT INTO tweets(id, text, time) VALUES(?,?,?)', new_tweets_list)
                db.commit()

        def create_list_of_tweets():
            # Takes the text of all tweets in the archive and makes them into a list

            cursor.execute('SELECT text FROM tweets')

            # The fetchall returns a list of tuples with one value each, we need them to be strings
            list_of_tweets_tuples = cursor.fetchall()

            # The list of strings
            list_of_tweets = []

            for tweet in list_of_tweets_tuples:
                list_of_tweets.append(tweet[0])

            return list_of_tweets

        self.archive = archive
        self.n = n

        db = sqlite3.connect(archive)
        cursor = db.cursor()

        update_archive()

        self.list_of_tweets = create_list_of_tweets()

        db.close()

    @staticmethod
    def create_word_pos(word, pos):
        all_parts = (word, pos)

        if all_parts in existing_word_pos:
            return existing_word_pos[all_parts]

        else:
            word_pos = WordAndPos(word, pos)
            existing_word_pos[all_parts] = word_pos
            return word_pos

    def create_word_bank(self):
        # Creates the nested dictionary of letters to use
        # n is the number of preceding characters that will be looked back upon to build the Markov chain

        word_bank = {}

        starter_list = []

        # Goes through every tweet in the archive
        for tweet in self.list_of_tweets:
            nlp_sentence = nlp(str(tweet))

            for index, token in enumerate(nlp_sentence):
                sequence = []

                i = 0
                try:
                    while i <= self.n:
                        sequence.append(((str(nlp_sentence[index + i])), nlp_sentence[index + i].pos_))
                        i += 1

                except IndexError:
                    break

                keys = tuple(sequence[:-1])
                next_word = sequence[-1]

                word_bank.setdefault(keys, {})
                word_bank[keys].setdefault(next_word, 0)
                word_bank[keys][next_word] += 1

            start = []

            for index, token in enumerate(nlp_sentence):
                if index is self.n:
                    break

                word = str(token)
                pos = token.pos_
                start.append((word, pos))

            starter_list.append(start)

        return word_bank, starter_list


# The db file that contains all of Trump's tweets
archiveFileName = 'TrumpTweets.db'

# The number of letters that will be used to build the chain
numberOfWordsUsed = 2

source = Source(archiveFileName, numberOfWordsUsed)

wordBank, starterList = source.create_word_bank()

with open('wordbank.pkl', 'wb') as file:
    pickle.dump(wordBank, file)

with open('starters.pkl', 'wb') as file:
    pickle.dump(starterList, file)

googleAuth = GoogleAuth()
googleAuth.LocalWebserverAuth()
drive = GoogleDrive(googleAuth)

for file in drive.ListFile().GetList():
    if file['title'] == 'wordbank.pkl':
        file.SetContentFile('wordbank.pkl')
        file.Upload()

    elif file['title'] == 'starters.pkl':
        file.SetContentFile('starters.pkl')
        file.Upload()

print('done')
