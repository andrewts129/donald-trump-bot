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
    texts = pd.read_csv(archive, usecols=[2], encoding="ISO-8859-1")
    source = list(set(texts['text']))

    wordBank = {}

    for tweet in source:
        for index, letter in enumerate(tweet):
            if len(tweet) >= n:
                letters = [letter]
                i = 1

                while i < n:
                    letters.append(tweet[index + i])
                    i += 1

                nested_set(wordBank, letters)

                if index == len(tweet) - n:
                    break

    starterTweet = random.choice(source)
    starter = starterTweet[0: n-1]
    return wordBank, starter


def create_tweet(wordBank, starter, n):
    output = list(starter)

    lastWordIsEnder = False

    while len(''.join(output)) < 130 and lastWordIsEnder is False:
        lastLetters = output[-n + 1:]

        try:
            totalChoices = sum(get_bottom_dict(wordBank, lastLetters).values())
            valuesListRaw = list(get_bottom_dict(wordBank, lastLetters).values())
            valuesListCorrected = []

        except (KeyError, ValueError, AttributeError):
            print("ERROR")
            return output

        for rawValue in valuesListRaw:
            correctedValue = rawValue / float(totalChoices)
            valuesListCorrected.append(correctedValue)

        listOfWords = list(get_bottom_dict(wordBank, lastLetters).keys())

        fourth = choice(listOfWords, 1, p=valuesListCorrected)[0]

        output.append(fourth)

        if ((output[-1] == '.' or output[-1] == '!' or output[-1] == '?') and len(''.join(output)) > 90):
            lastWordIsEnder = True

    return output


def post_tweet(tweet):
    # Converts the tweet list to a string for tweeting purposes
    tweetString = ' '.join(tweet)
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


def find_time_to_sleep(timeList):
    targetHour = timeList[0]
    targetMinute = timeList[1]

    timeNow = datetime.datetime.now()
    nowHour = timeNow.hour
    nowMinute = timeNow.minute

    totalTargetSeconds = (60 * 60 * targetHour) + (60 * targetMinute)
    totalNowSeconds = (60 * 60 * nowHour) + (60 * nowMinute)
    timeTil = totalTargetSeconds - totalNowSeconds

    if timeTil < 0:
        timeTil = 86400 + timeTil

    return timeTil


def follow_people():
    trumpFollowers = api.followers('realDonaldTrump')
    for user in trumpFollowers:
        userID = user.id
        api.create_friendship(userID)


def get_tweets_to_reply_to():
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
    tweet.insert(0, '@' + user)

    # If the tweet is over 140 characters, try again
    while len(''.join(tweet)) > 140:
        tweet = create_tweet(wordBank, firstBank, n)
        tweet.insert(0, '@' + user)

    print(''.join(tweet))

    tweetString = ''.join(tweet)
    api.update_status(tweetString, in_reply_to_status_id=id_to_reply_to)


def reply_to_people(archive, n):
    tweetsToReplyTo = get_tweets_to_reply_to()
    list_of_favorited_ids = get_list_of_favorited_tweets_ids()

    for tweet in tweetsToReplyTo:
        if tweet.id not in list_of_favorited_ids:
            reply(archive, tweet.id, n)
            api.create_favorite(tweet.id)


def get_list_of_favorited_tweets_ids():
    listy = api.favorites()
    listOfIds = []
    for i in listy:
        listOfIds.append(i.id)

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
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic.setdefault(keys[-1], 0)
    dic[keys[-1]] += 1


def get_bottom_dict(dic, keys):
    for key in keys:
        dic = dic.get(key)
    return dic


# Twitter Authentication
auth = tweepy.OAuthHandler("private", "private")
auth.set_access_token("private", "private")
api = tweepy.API(auth)

archive = 'TrumpTweetsArchive.csv'

n = 12

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
            break
        else:
            time.sleep(300)
