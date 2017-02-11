import random
import tweepy
from numpy.random import choice
import pickle
import requests

print('Waking up...')

# Setting up for using the Twitter API
auth = tweepy.OAuthHandler(consumer_key='private',
                           consumer_secret='private')

auth.set_access_token(key='private',
                      secret='private')

api = tweepy.API(auth)


def create_word_bank():
    # Downloads the word bank containing all the words (and their part of speech), as well as the two words that precede
    # them
    url = "https://drive.google.com/uc?id=0B8xDokak7DY3OGxuLVo5d1loZTA"
    word_bank_pickle = requests.get(url).content
    print("Downloaded word bank...")
    word_bank = pickle.loads(word_bank_pickle)

    return word_bank


def get_starter_letters():
    # Randomly picks a Trump tweet and takes the starting two words from it to start building the chain.
    url = "https://drive.google.com/uc?id=0B8xDokak7DY3S3p0RUppZUNRTWs"
    starter_pickle = requests.get(url).content
    print("Downloaded starter words...")
    all_starters = pickle.loads(starter_pickle)

    starter_letters = random.choice(all_starters)

    return starter_letters


class TweetBuilder(object):
    # Handles the construction of the Markov chain

    def __init__(self, n):
        # The number of letters that will be used to build the chain
        self.n = n

    def create_tweet(self, username_to_reply_to):
        # Creates a string that can be tweeted out. If it's not supposed to be a reply to anybody, set
        # username_to_reply_to to be an empty string

        def chain_to_string(chain_list):
            # Takes a chain of words and parts of speech and turns the words into a string
            out_string = ""

            for item in chain_list:
                # The first chunk of each tuple is the word (second part is the part of speech)
                out_string = out_string + item[0] + ' '

            # Lots of little minor adjustments that make the output text look a little more natural
            out_string = out_string.replace(" ’", "’")
            out_string = out_string.replace(" !", "!")
            out_string = out_string.replace(" .", ".")
            out_string = out_string.replace(" ?", "?")
            out_string = out_string.replace("# ", "#")
            out_string = out_string.replace("( ", "(")
            out_string = out_string.replace(" )", ")")
            out_string = out_string.replace(" ,", ",")
            out_string = out_string.replace(" ;", ";")
            out_string = out_string.replace(" '", "'")
            out_string = out_string.replace(" n'", "n'")
            out_string = out_string.replace(" :", ":")
            out_string = out_string.replace(" %", "%")
            out_string = out_string.replace('"', '')
            out_string = out_string.replace('“', '')
            out_string = out_string.replace('”', '')
            out_string = out_string.replace(" - ", "-")
            out_string = out_string.replace("   ", " ")
            out_string = out_string.replace("  ", " ")
            out_string = out_string.strip()

            return out_string

        def create_markov():
            # Uses a Markov chain to create a tweet imitating Donald Trump
            # Returns the tweet in a string

            def create_p_values(numbers):
                # When given a list of numbers, adjusts it so that all the numbers add up to 1
                # (but keep the same ratios between them)
                total_sum = sum(numbers)

                output = []

                for number in numbers:
                    p = float(number) / total_sum
                    output.append(p)

                return output

            # Calculates the amount of space to leave for @username if the tweet is a reply
            if len(username_to_reply_to) is 0:
                space_to_leave = 0
            else:
                space_to_leave = len(username_to_reply_to) + 2

            word_bank = create_word_bank()

            # Starts the tweet by adding the first few characters of an actual @realDonaldTrump tweet
            chain = get_starter_letters()

            # Converts the fledgling chain into a string so that the length of the output can be checked
            chain_string = chain_to_string(chain)

            # Need to leave room for the @username if it's a reply
            while len(chain_string) < 140 - space_to_leave:
                # Gets the last few words to use as the source for the next word
                last_word_pos = tuple(chain[-self.n:])

                try:
                    possible_next_word_pos = list(word_bank[last_word_pos].keys())

                # If there is a key error, that means that the last sequence in the string only ever appeared at the end
                # of a tweet (since nothing ever came after it that was put into the dictionary). Therefore, it's a good
                # place to end.
                except KeyError:
                    print("ERROR")
                    break

                # Gets p-values based on the frequency of each word after the sequence to determine the probabilities
                # that each word should be chosen
                possible_next_values = list(word_bank[last_word_pos].values())
                possible_next_values = create_p_values(possible_next_values)

                # Chooses the next word according to the p-values
                next_word_pos = possible_next_word_pos[choice(len(possible_next_word_pos), p=possible_next_values)]
                chain.append(next_word_pos)

                # If the last letter of the tweet so far is a punctuation and the tweet is already 90 characters,
                # call it done
                chain_string = chain_to_string(chain)
                if chain_string[-1] in '.?!' and len(chain_string) > 90:
                    break

            return chain_string

        def refine_markov_for_tweeting(tweet_string_raw):
            # Fixes some common problems that the Markov generator encounters, as well as converts it to a string
            tweet_list_words = tweet_string_raw.split()

            # If the bot is supposed to be tweeting at somebody and the markov chain generated a tweet that starts with
            # @somebody, remove the @somebody. It doesn't need to bring anybody else into the conversation.
            # If it's not supposed to be tweeting at anybody, leave it, but put a period at the beginning so it appears
            # on everybody's time line.
            if tweet_list_words[0][0] is '@':
                if len(username_to_reply_to) is not 0:
                    del tweet_list_words
                else:
                    tweet_list_words[0] = '.' + tweet_list_words[0]

            # This will be the list of words after some modifications might be made
            better_tweet_list_words = []

            for index, word in enumerate(tweet_list_words):

                # At some point during this program, ampersands get messed up. This fixes it.
                if word == '&amp;' or word == '&amp':
                    better_tweet_list_words.append('&')

                # Sometimes the chain will end on the period in a link. If so, do not include it
                elif word != 'https://t.' or word != 'http://t.':
                    better_tweet_list_words.append(word)

            # If the bot is supposed to be talking to somebody, make it @ them
            if len(username_to_reply_to) is not 0:
                better_tweet_list_words.insert(0, '@' + username_to_reply_to)

            # Returns a string of the completed tweet
            return ' '.join(better_tweet_list_words)

        tweet_string = refine_markov_for_tweeting(create_markov())

        # The tweet should be under 140 characters, but if it isn't, try again until it is
        while len(tweet_string) > 140:
            tweet_string = refine_markov_for_tweeting(create_markov())

        return tweet_string


class Bot(object):
    def __init__(self, tweet_builder, minutes_between_reply_checks, number_of_times_to_tweet_per_day):

        self.tweet_builder = tweet_builder

        # Checks to see if somebody has tweeted at @DonaldTrumBot every __ seconds
        self.seconds_between_reply_checks = minutes_between_reply_checks * 60

        # On average, the number of times it should tweet per day (not counting replies)
        self.number_of_times_to_tweet_per_day = number_of_times_to_tweet_per_day

        # Calculates the number of times TrumBot will wake up and check to see if it's time to reply by taking the total
        # number of seconds in a day and dividing it by the seconds between checks
        self.number_of_check_intervals_per_day = (24 * 60 * 60) / self.seconds_between_reply_checks

        # Every time the bot wakes up, it selects a random number from this list. If it chooses 0, it tweets. It should
        # pick 0 however many times a day it is set to tweet
        self.listy = list(range(0, int(self.number_of_check_intervals_per_day / number_of_times_to_tweet_per_day)))

    def check_if_time_to_tweet(self):
        # Checks if it's time to tweet
        random_number = random.choice(self.listy)

        if True:
        #if random_number is 0:
            print('Tweeting...')
            return True
        else:
            print('Not tweeting...')
            return False

    def reply_to_people(self):
        # Replies to everybody that has tweeted at DonaldTrumBot

        def get_tweets_to_reply_to():
            # Gets the tweets that are directed at TrumBot
            replies_to_me = api.search('@DonaldTrumBot')

            # Adds the ID of all non-retweets to a list
            for reply in replies_to_me:
                if hasattr(reply, 'retweeted_status'):
                    replies_to_me.remove(reply)

            return replies_to_me

        def get_list_of_favorited_tweets_ids():
            # Gets a list of every tweet that TrumBot has favorited
            list_of_ids = []

            for favorited_tweet in tweepy.Cursor(api.favorites).items():
                list_of_ids.append(favorited_tweet.id)

            return list_of_ids

        # DonaldTrumBot favorites a tweet after it replies, so it knows not to reply to it again
        tweets_to_reply_to = get_tweets_to_reply_to()
        list_of_favorited_ids = get_list_of_favorited_tweets_ids()

        for tweet in tweets_to_reply_to:
            if tweet.id not in list_of_favorited_ids:
                username = tweet.author.screen_name
                print('Replying to @' + username + '...')
                string_to_tweet = self.tweet_builder.create_tweet(username_to_reply_to=username)

                api.update_status(string_to_tweet, in_reply_to_status_id=tweet.id)

                api.create_favorite(tweet.id)

    def wake_up(self):
        # This runs every time DonaldTrumBot wakes up
        self.reply_to_people()

        # Runs if it is time to tweet
        if self.check_if_time_to_tweet():
            string_to_tweet = self.tweet_builder.create_tweet(username_to_reply_to='')
            print(string_to_tweet)
            #api.update_status(string_to_tweet)


# The db file that contains all of Trump's tweets
archiveFileName = 'TrumpTweets.db'

# The number of letters that will be used to build the chain
numberOfWordsUsed = 2

# Creates the object that builds the Markov chains turns them into tweets
tweetBuilder = TweetBuilder(n=numberOfWordsUsed)

# Creates the object that interfaces with Twitter
donaldTrumBot = Bot(tweet_builder=tweetBuilder, minutes_between_reply_checks=10,
                    number_of_times_to_tweet_per_day=3)

# This runs through all the functions the bot should do and things it should check
donaldTrumBot.wake_up()

print('Going back to sleep...')
