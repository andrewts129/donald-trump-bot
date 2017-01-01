import random
import tweepy
import pandas as pd
from numpy.random import choice
import time

# Setting up for using the Twitter API
auth = tweepy.OAuthHandler(consumer_key='r33lYBUS2murfH4laSDXOnMmr',
                           consumer_secret='t3qVrYYeAfK3kWPkY3LnP20z0QfMl1TPr0Q6WZm4Olt61VKkpx')

auth.set_access_token(key='797971904258772996-42sBRXzXu6o4o7lquisdw3RsZ3uoJ3l',
                      secret='RzeKkSzzd5kbzrr0NOu2z3J6E5AULCO6xVUuVVyx9r2NC')

api = tweepy.API(auth)


class Source(object):
    # Handles the source of tweets that are used to construct the Markov chain

    def __init__(self, archive, n):
        def update_archive():
            # Updates the csv file with all the tweets that are not in it yet

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

            # Imports the csv archive and finds the tweet in there with the highest id i.e the newest one
            ids = pd.read_csv(self.archive, usecols=[1])
            ids_list = list(set(ids['id']))
            newest_id = max(ids_list)

            # If the last tweet in the archive isn't the last thing tweeted, download all new tweets
            last_tweet_id = int(api.user_timeline(screen_name='@realDonaldTrump', count=200)[0].id_str)

            if newest_id < last_tweet_id:

                new_tweets = download_new_tweets(newest_id)

                # Creates a list of dictionaries with tweet id and text as keys
                new_tweets_dicts = []

                for tweet in new_tweets:
                    text = tweet.text
                    tweet_id = tweet.id_str
                    time = str(tweet.created_at.hour) + ':' + str(tweet.created_at.minute)

                    if 'RT @' and '"@' not in text:
                        data = {'id': tweet_id, 'text': text, 'time': time}
                        new_tweets_dicts.append(data)

                # Appends the data to the end of the archive
                df = pd.DataFrame(new_tweets_dicts)
                df.to_csv(self.archive, mode='a', header=False)

        def create_list_of_tweets():
            # Takes the text of all tweets in the archive and makes them into a list
            texts = pd.read_csv(self.archive, usecols=[2], encoding="ISO-8859-1")
            source = list(set(texts['text']))

            return source

        self.archive = archive
        self.n = n

        update_archive()

        self.list_of_tweets = create_list_of_tweets()

    def create_letter_bank(self):
        # Creates the nested dictionary of letters to use
        # n is the number of preceding characters that will be looked back upon to build the Markov chain

        def nested_set(dic, keys):
            # Adds one to the value of the lowest dictionary in a nested dictionary, given a list of keys to look down
            # through

            for key in keys[:-1]:
                dic = dic.setdefault(key, {})
            dic.setdefault(keys[-1], 0)
            dic[keys[-1]] += 1

        letter_bank = {}

        # Goes through every tweet in the archive
        for tweet in self.list_of_tweets:
            # Goes through every letter in the tweet
            for index, letter in enumerate(tweet):
                # The tweet can only be processed if there are at least n letters
                if len(tweet) >= self.n:
                    # Builds a list of each sequence of letters of n length in the tweet
                    letters = [letter]
                    i = 1

                    while i < self.n:
                        letters.append(tweet[index + i])
                        i += 1

                    # Adds one to the number of times each sequence has appeared
                    nested_set(letter_bank, letters)

                    if index == len(tweet) - self.n:
                        break

        return letter_bank

    def get_starter_letters(self):
        # Picks a random tweet and uses the first n characters as the starting point for the Markov chain
        starter_tweet = random.choice(self.list_of_tweets)
        starter_letters = starter_tweet[0: self.n - 1]

        return starter_letters


class TweetBuilder(object):
    # Handles the construction of the Markov chain

    def __init__(self, source_object, n):

        self.source_object = source_object

        # The number of letters that will be used to build the chain
        self.n = n

    def create_tweet(self, username_to_reply_to):
        # Creates a string that can be tweeted out. If it's not supposed to be a reply to anybody, set
        # username_to_reply_to to be an empty string

        def create_markov():
            # Uses a Markov chain to create a tweet imitating Donald Trump
            # Returns the tweet in a list of characters

            def get_bottom_dict(dic, keys):
                # Returns the bottom-most dictionary in a nested dictionary, given a list of keys to look down through
                for key in keys:
                    dic = dic.get(key)
                return dic

            # Calculates the amount of space to leave for @username if the tweet is a reply
            if len(username_to_reply_to) is 0:
                space_to_leave = 0
            else:
                space_to_leave = len(username_to_reply_to) + 2

            letter_bank = self.source_object.create_letter_bank()

            # Starts the tweet by adding the first few characters of an actual @realDonaldTrump tweet
            starter_letters = self.source_object.get_starter_letters()
            output_tweet = list(starter_letters)

            # This becomes true when the tweet has found a good stopping point
            last_word_is_ender = False

            # Need to leave room for the @username if it's a reply
            while len(''.join(output_tweet)) < 140 - space_to_leave and last_word_is_ender is False:
                # Finds the last few letters of the tweet for the Markov chain to build on
                last_letters = output_tweet[-self.n + 1:]

                # Finds the bottom dictionary in the sequence, the one that has the finals letters and their frequency
                try:
                    bottom_dict = get_bottom_dict(letter_bank, last_letters)

                    # Looks for the letters that have come after the preceding sequence
                    # Total number of times that sequence has appeared
                    total_choices = sum(bottom_dict.values())

                # If there is an error, nothing has come after that sequence, meaning it has only appeared at the end of
                # a tweet and therefore is probably a good place to end
                except (KeyError, ValueError, AttributeError):
                    print("ERROR")
                    return output_tweet

                # Gets the number of times each letter has appeared after the sequence, for p-values
                values_list_raw = list(bottom_dict.values())
                values_list_corrected = []

                # Converts the number of times each letter has appeared into p-values by dividing by the total number of
                # times some letter has come after the sequence
                for rawValue in values_list_raw:
                    corrected_value = rawValue / float(total_choices)
                    values_list_corrected.append(corrected_value)

                # Gets a list of all the letters that have come after the sequence
                list_of_letters = list(bottom_dict.keys())

                # Chooses a letter from the list using the p-values created above
                new_letter = choice(list_of_letters, 1, p=values_list_corrected)[0]

                output_tweet.append(new_letter)

                # If the last letter of the tweet so far is a punctuation and the tweet is already 90 characters,
                # call it done
                if output_tweet[-1] in '.!?' and len(''.join(output_tweet)) > 90:
                    last_word_is_ender = True

            return output_tweet

        def refine_markov_for_tweeting(tweet_list_chars):
            # Fixes some common problems that the Markov generator encounters, as well as converts it to a string

            # Most problems occur at the word level, not character, so convert it into a list of words instead
            tweet_list_words = ''.join(tweet_list_chars).split()

            # If the bot is supposed to be tweeting at somebody and the markov chain generated a tweet that starts with
            # @somebody, remove the @somebody. It doesn't need to bring anybody else into the conversation.
            # If it's not supposed to be tweeting at anybody, leave it, but put a period at the beginning so it appears
            # on everybody's time line.
            if tweet_list_words[0][0] is '@':
                if len(username_to_reply_to) is not 0:
                    del tweet_list_words
                else:
                    tweet_list_words[0] = '.' + tweet_list_words[0]

            for index, word in enumerate(tweet_list_words):

                # Sometimes the chain will end at the period in a link. If so, remove it
                if word is 'https://t.' or word is 'http://t.':
                    del tweet_list_words[index]

                # At some point during this program, ampersands get messed up. This fixes it.
                elif word is '&amp;' or word is '&amp':
                    tweet_list_words[index] = '&'

            # If the bot is supposed to be talking to somebody, make it @ them
            if len(username_to_reply_to) is not 0:
                tweet_list_words.insert(0, '@' + username_to_reply_to)

            # Returns a string of the completed tweet
            return ' '.join(tweet_list_words)

        # All the letter sequences in all Trump's tweets, with the number of times each occured

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

        if random_number == 0:
            return True
        else:
            return False

    def reply_to_people(self):
        # Replies to everybody that has tweeted at DonaldTrumBot

        def get_tweets_to_reply_to():
            # Gets the tweets that are directed at TrumBot
            replies_to_me = api.search('@DonaldTrumBot')

            # Adds the ID of all non-retweets to a list
            for tweet in replies_to_me:
                if hasattr(tweet, 'retweeted_status'):
                    replies_to_me.remove(tweet)

            return replies_to_me

        def get_list_of_favorited_tweets_ids():
            # Gets a list of every tweet that TrumBot has favorited
            list_of_ids = []

            for tweet in tweepy.Cursor(api.favorites).items():
                list_of_ids.append(tweet.id)

            return list_of_ids

        # DonaldTrumBot favorites a tweet after it replies, so it knows not to reply to it again
        tweets_to_reply_to = get_tweets_to_reply_to()
        list_of_favorited_ids = get_list_of_favorited_tweets_ids()

        for tweet in tweets_to_reply_to:
            if tweet.id not in list_of_favorited_ids:
                username = tweet.author.screen_name
                string_to_tweet = self.tweet_builder.create_tweet(username_to_reply_to=username)

                api.update_status(string_to_tweet, in_reply_to_status_id=tweet.id)

                api.create_favorite(tweet.id)

    @staticmethod
    def unfollow_people():
        # Unfollows people who have not followed back (gotta keep that ratio good)
        my_followers = api.followers_ids()
        following = api.friends_ids()

        # Excludes the 40 most recent followers, give them some time to decide
        following = following[:-40]

        # People that are allowed to not follow me back
        whitelist = [25073877, 705113652471439361, 805070473839177728, 799735756411408384, 804438219676712960]

        for user in following:
            if user not in my_followers and user not in whitelist:
                api.destroy_friendship(id=user)

    @staticmethod
    def follow_people():
        # Follows people who have recently followed the real Trump
        trump_followers = api.followers('realDonaldTrump')

        for user in trump_followers:
            user_id = user.id
            api.create_friendship(user_id)

        # Follows people who have recently tweeted about Trump
        search_results = api.search('Trump')

        for tweet in search_results:
            user_id = tweet.author.id
            api.create_friendship(user_id)

    def wake_up(self):
        # This runs every time DonaldTrumBot wakes up
        self.reply_to_people()

        # Runs if it is time to tweet
        if self.check_if_time_to_tweet():
            string_to_tweet = self.tweet_builder.create_tweet(username_to_reply_to='')
            api.update_status(string_to_tweet)

            Bot.unfollow_people()
            Bot.follow_people()

# The csv file that contains all of Trump's tweets
csvFileName = 'TrumpTweetsArchive.csv'

# The number of letters that will be used to build the chain
numberOfLettersUsed = 11

# Creates the object that processes all of the tweets in the csv file
source = Source(archive=csvFileName, n=numberOfLettersUsed)

tweetBuilder = TweetBuilder(source_object=source, n=numberOfLettersUsed)

donaldTrumBot = Bot(tweet_builder=tweetBuilder, minutes_between_reply_checks=5,
                    number_of_times_to_tweet_per_day=1)

while True:
    donaldTrumBot.wake_up()
    time.sleep(donaldTrumBot.seconds_between_reply_checks)
