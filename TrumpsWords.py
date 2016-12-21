import random
import tweepy
import pandas as pd
import time
import datetime
from numpy.random import choice


def create_source(archive):
    # Imports the csv archive and finds the tweet in there with the highest id i.e the newest one
    ids = pd.read_csv(archive, usecols=[1])
    idsList = list(set(ids['id']))
    newestId = max(idsList)

    # If the last tweet in the archive isn't the last thing tweeted, download all new tweets
    lastTweetId = int(api.user_timeline(screen_name='@realDonaldTrump', count=200)[0].id_str)

    if newestId < lastTweetId:
        newTweets = download_new_tweets(newestId)

        # Creates a list of dictionaries with tweet id and text as keys
        newTweetsDicts = []

        for tweet in newTweets:
            text = tweet.text
            tweetID = tweet.id_str
            time = str(tweet.created_at.hour) + ':' + str(tweet.created_at.minute)

            if 'RT @' and '"@' not in text:
                data = {'id': tweetID, 'text': text, 'time': time}
                newTweetsDicts.append(data)

        # Appends the data to the end of the archive
        df = pd.DataFrame(newTweetsDicts)
        df.to_csv(archive, mode='a', header=False)


def download_new_tweets(newestId):
    # Gets all the newest tweets that aren't yet in the archive
    alltweets = []

    # make initial request for most recent tweets (200 is the maximum allowed count)
    new_tweets = api.user_timeline(screen_name='@realDonaldTrump', count=200, since_id=newestId)

    # save most recent tweets
    alltweets.extend(new_tweets)

    # save the id of the oldest tweet less one
    oldest = alltweets[-1].id - 1

    # keep grabbing tweets until there are no tweets left to grab
    while len(new_tweets) > 0:
        # all subsequent requests use the max_id param to prevent duplicates
        new_tweets = api.user_timeline(screen_name='@realDonaldTrump', count=200, max_id=oldest, since_id=newestId)

        # save most recent tweets
        alltweets.extend(new_tweets)

        # update the id of the oldest tweet less one
        oldest = alltweets[-1].id - 1

    return alltweets


def create_word_bank(archive , n):
    # Creates the nested dictionary of letters to use, as well as the first few letters to start the tweet off with
    # n is the number of preceding characters that will be looked back upon to build the Markov chain
    texts = pd.read_csv(archive, usecols=[2], encoding="ISO-8859-1")
    source = list(set(texts['text']))

    wordBank = {}

    # Goes through every tweet in the archive
    for tweet in source:
        # Goes through every letter in the tweet
        for index, letter in enumerate(tweet):
            # The tweet can only be processed if there are at least n letters
            if len(tweet) >= n:
                # Builds a list of each sequence of letters of n length in the tweet
                letters = [letter]
                i = 1

                while i < n:
                    letters.append(tweet[index + i])
                    i += 1

                # Adds one to the number of times each sequence has appeared
                nested_set(wordBank, letters)

                if index == len(tweet) - n:
                    break

    # Picks a random tweet and uses the first n characters as the starting point for the Markov chain
    starterTweet = random.choice(source)
    starter = starterTweet[0: n-1]
    return wordBank, starter


def create_tweet(wordBank, starter, n):
    # Uses a Markov chain to create a tweet imitating Donald Trump

    # Starts the tweet by adding the first few characters of an actual @realDonaldTrump tweet
    output = list(starter)

    # This becomes true when the tweet has found a good stopping point
    lastWordIsEnder = False

    while len(''.join(output)) < 140 and lastWordIsEnder is False:
        # Finds the last few letters of the tweet for the Markov chain to build on
        lastLetters = output[-n + 1:]

        # Finds the bottom dictionary in the sequence, the one that has the finals letters and their frequency
        try:
            bottomDict = get_bottom_dict(wordBank, lastLetters)

            # Looks for the letters that have come after the preceding sequence
            # Total number of times that sequence has appeared
            totalChoices = sum(bottomDict.values())

        # If there is an error, nothing has come after that sequence, meaning it has only appeared at the end of a tweet
        # and therefore is ready to post
        except (KeyError, ValueError, AttributeError):
            print("ERROR")
            if output[0] == '@':
                output.insert(0, '.')
            return output

        # Gets the number of times each letter has appeared after the sequence, for p-values
        valuesListRaw = list(bottomDict.values())
        valuesListCorrected = []

        # Converts the number of times each letter has appeared into p-values by dividing by the total number of times
        # some letter has come after the sequence
        for rawValue in valuesListRaw:
            correctedValue = rawValue / float(totalChoices)
            valuesListCorrected.append(correctedValue)

        # Gets a list of all the letters that have come after the sequence
        listOfLetters = list(bottomDict.keys())

        # Chooses a letter from the list using the p-values created above
        newLetter = choice(listOfLetters, 1, p=valuesListCorrected)[0]

        output.append(newLetter)

        # If the last letter of the tweet so far is a punctuation and the tweet is already 90 characters, called it done
        if output[-1] in '.!?' and len(''.join(output)) > 90:
            lastWordIsEnder = True

    # Adds a . if tweeting directly at somebody so it shows up on all timelines
    if output[0] == '@':
        output.insert(0, '.')

    return output


def post_tweet(tweet):
    # Puts the final touches on the tweet and then posts it
    # Converts the tweet list to a string for tweeting purposes
    tweetString = ''.join(tweet)

    # Makes sure the ampersands are represented correctly in the tweet
    tweetString = replace_amp(tweetString)
    tweetString = removed_hanging_link(tweetString)
    api.update_status(tweetString)


def regular_tweet(archive, n):
    # Calling this causes the TrumpBot to create a tweet and then post it

    # Loads and updates the tweet archive
    create_source(archive)

    # Uses the archive to create a word bank of all of Trump's tweets' words and the words that came before
    wordBank, starter = create_word_bank(archive, n)

    # Uses the word bank to construct a Markov chain
    tweet = create_tweet(wordBank, starter, n)

    # If the tweet is over 140 characters, try again
    while len(''.join(tweet)) > 140:
        tweet = create_tweet(wordBank, starter, n)

    print(''.join(tweet))

    post_tweet(tweet)


def get_next_tweet_time(archive):
    # Determines the next time that TrumBot should tweet by finding the time of a real Trump tweet
    times = pd.read_csv(archive, usecols=[3])
    listy = list(set(times['time']))
    # First value is an invalid thing called nan, causes trouble later
    del listy[0]
    rawTime = random.choice(listy)
    posOfColon = rawTime.find(':')
    hourOfNextTweet = int(rawTime[0:posOfColon])
    minuteOfNextTweet = int(rawTime[posOfColon + 1: len(rawTime)])
    timeList = [hourOfNextTweet, minuteOfNextTweet]
    return timeList


def follow_people():
    # Follows people who have recently followed Trump
    trumpFollowers = api.followers('realDonaldTrump')

    for user in trumpFollowers:
        userID = user.id
        api.create_friendship(userID)

    # Follows people who have recently tweeted about Trump
    searchResults = api.search('Trump')

    for tweet in searchResults:
        userID = tweet.author.id
        api.create_friendship(userID)


def unfollow_people():
    # Unfollows people who have not followed back (gotta keep that ratio good)
    myFollowers = api.followers_ids()
    following = api.friends_ids()

    # Excludes the 50 most recent followers, give them some time to decide
    following = following[-50:]

    # People that are allowed to not follow me back
    whitelist = [25073877, 705113652471439361, 805070473839177728, 799735756411408384, 804438219676712960]

    for user in following:
        if user not in myFollowers and user not in whitelist:
            api.destroy_friendship(id=user)


def get_tweets_to_reply_to():
    # Gets the tweets that are directed at TrumBot
    repliesToMe = api.search('@DonaldTrumBot')

    # Adds the ID of all non-retweets to a list
    for tweet in repliesToMe:
        if hasattr(tweet, 'retweeted_status'):
            repliesToMe.remove(tweet)

    return repliesToMe


def reply(archive, id_to_reply_to, n):
    # Calling this causes the TrumpBot to reply to the tweet with the given ID

    # Loads the tweet with the given ID as a status and finds the username of the author
    tweetToReplyTo = api.get_status(id_to_reply_to)
    user = tweetToReplyTo.user.screen_name

    # Loads and updates the tweet archive
    create_source(archive)

    # Uses the archive to create a word bank of all of Trump's tweets' words and the words that came before
    wordBank, firstBank = create_word_bank(archive, n)

    # Uses the word bank to construct a Markov chain
    tweet = create_tweet(wordBank, firstBank, n)
    tweet.insert(0, '@' + user + ' ')

    # If the tweet is over 140 characters, try again
    while len(''.join(tweet)) > 140:
        tweet = create_tweet(wordBank, firstBank, n)
        tweet.insert(0, '@' + user + ' ')

    print(''.join(tweet))

    tweetString = ''.join(tweet)
    tweetString = replace_amp(tweetString)
    tweetString = removed_hanging_link(tweetString)
    api.update_status(tweetString, in_reply_to_status_id=id_to_reply_to)


def reply_to_people(archive, n):
    # Replies to everybody that has tweeted at TrumBot
    # TrumBot favorites a tweet after it replies, so it knows not to reply to it again
    tweetsToReplyTo = get_tweets_to_reply_to()
    list_of_favorited_ids = get_list_of_favorited_tweets_ids()

    for tweet in tweetsToReplyTo:
        if tweet.id not in list_of_favorited_ids:
            reply(archive, tweet.id, n)
            api.create_favorite(tweet.id)


def get_list_of_favorited_tweets_ids():
    # Gets a list of every tweet that TrumBot has favorited
    listOfIds = []

    for tweet in tweepy.Cursor(api.favorites).items():
        listOfIds.append(tweet.id)

    return listOfIds


def list_to_datetime(timeList):
    hour = timeList[0]
    minute = timeList[1]

    now = datetime.datetime.now()
    target = now.replace(hour=hour, minute=minute)

    if target < now:
        target = target + datetime.timedelta(days=1)

    return target


def nested_set(dic, keys):
    # Adds one to the value of the lowest dictionary in a nested dictionary, given a list of keys to look down through
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic.setdefault(keys[-1], 0)
    dic[keys[-1]] += 1


def get_bottom_dict(dic, keys):
    # Returns the bottom-most dictionary in a nested dictionary, given a list of keys to look down through
    for key in keys:
        dic = dic.get(key)
    return dic


def replace_amp(text):
    text = text.replace('&amp;', '&')
    text = text.replace('&amp', '&')

    return text


def removed_hanging_link(text):
    # Sometimes the tweet will finished with an unfinished link, like http://t. This removes it
    endOfString = text[-10:]
    if 'https://t.' in endOfString:
        text.replace('https://t.', '')
    elif 'http://t.' in endOfString:
        text.replace('http://t.', '')
    return text


# Twitter Authentication
auth = tweepy.OAuthHandler("private", "private")
auth.set_access_token("private", "private")
api = tweepy.API(auth)

archive = 'TrumpTweetsArchive.csv'

n = 11

while True:
    nextTweetTimeList = get_next_tweet_time(archive)
    nextTweetTime = list_to_datetime(nextTweetTimeList)
    print(nextTweetTime)
    print(nextTweetTimeList)
    while True:
        reply_to_people(archive, n)
        if nextTweetTime < datetime.datetime.now():
            regular_tweet(archive, n)
            follow_people()
            unfollow_people()
            break
        else:
            time.sleep(300)
