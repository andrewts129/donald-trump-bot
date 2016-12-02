import random
import tweepy
import pandas as pd
import time
import datetime


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


def create_word_bank(source):
    # Loads all the texts of the tweets and places them in a list
    texts = pd.read_csv(source, usecols=[2], encoding="ISO-8859-1")
    tweets = list(set(texts['text']))

    # First value is an invalid thing called nan, causes trouble later
    del tweets[0]

    word_bank = []

    for tweet in tweets:
        # Divides each tweets' texts into individual words
        tweet = str(tweet)
        words = tweet.split()

        # The first word had no word before it. After the first word, this is changed to the previous word processed
        before_word = ""

        # Sorts the individual words into dictionaries with the current and before word, for use in Markov chain later
        for word in words:
            before_and_current = {'before': before_word, 'current': word}
            before_word = word
            word_bank.append(before_and_current)

    return word_bank


def create_tweet(wordBank):
    start = time.time()

    firstWord = ''
    outputList = []

    # Finds a word that had no word before it (aka a first word) and makes it the start of the chain
    while firstWord == '':
        r = random.choice(wordBank)

        if r['before'] == '' and r['current'][0] != '"':
            firstWord = r['current']
            outputList.append(firstWord)

    # Turns the list that was created into a string so the overall length can be checked
    outputString = ' '.join(outputList)
    print(outputList)

    # An ender word is one that signals a good end of a tweet
    lastWordIsEnder = False

    # Creation of the Markov chain
    while (len(outputString) < 130) and (lastWordIsEnder == False):
        newWord = ''

        # Keeps looping until a match is found
        while newWord == '':

            # Selects a random word in the bank and checks the word that came before it in the original tweet
            # If the before word matches the last currently in the chain, add it
            # This is probably a horribly inefficient way of doing this
            r = random.choice(wordBank)
            if r['before'] == outputList[-1]:
                newWord = r['current']
                if '&amp' in newWord:
                    newWord = '&'
                outputList.append(newWord)

            end = time.time()

            # If it hangs for too long, have it go ahead anyway because it's usually the end of a sentence anyway
            if end - start > 15:
                print("Timed out. Posting anyway")
                return outputList

        # Turns the list that was created into a string so the overall length can be checked
        outputString = ' '.join(outputList)
        print(outputList)

        # If the last letter is a . or ! or ? and the tweet is getting long, end it.
        # Also end if the last word is actually a link, because it can't continue from there
        if ((outputList[-1][-1] == '.' or outputList[-1][-1] == '!' or outputList[-1][-1] == '?') and len(outputString) > 90) or ('http' in newWord):
            lastWordIsEnder = True

    return outputList


def post_tweet(tweet):
    # Converts the tweet list to a string for tweeting purposes
    tweetString = ' '.join(tweet)
    api.update_status(tweetString)


def regular_tweet(archive):
    # Calling this causes the TrumpBot to create a tweet and then post it

    # Loads and updates the tweet archive
    create_source(archive)

    # Uses the archive to create a word bank of all of Trump's tweets' words and the words that came before
    wordBank = create_word_bank(archive)

    # Uses the word bank to construct a Markov chain
    tweet = create_tweet(wordBank)

    # If the tweet is over 140 characters, try again
    while len(' '.join(tweet)) > 140:
        tweet = create_tweet(wordBank)

    print(' '.join(tweet))

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


def reply(archive, id_to_reply_to):
    # Calling this causes the TrumpBot to reply to the tweet with the given ID

    # Loads the tweet with the given ID as a status and finds the username of the author
    tweetToReplyTo = api.get_status(id_to_reply_to)
    user = tweetToReplyTo.user.screen_name

    # Loads and updates the tweet archive
    create_source(archive)

    # Uses the archive to create a word bank of all of Trump's tweets' words and the words that came before
    wordBank = create_word_bank(archive)

    # Uses the word bank to construct a Markov chain
    tweet = create_tweet(wordBank)
    tweet.insert(0, '@' + user)

    # If the tweet is over 140 characters, try again
    while len(' '.join(tweet)) > 140:
        tweet = create_tweet(wordBank)
        tweet.insert(0, '@' + user)

    print(' '.join(tweet))

    tweetString = ' '.join(tweet)
    api.update_status(tweetString, in_reply_to_status_id=id_to_reply_to)


def reply_to_people(archive):
    tweetsToReplyTo = get_tweets_to_reply_to()
    list_of_favorited_ids = get_list_of_favorited_tweets_ids()

    for tweet in tweetsToReplyTo:
        if tweet.id not in list_of_favorited_ids:
            reply(archive, tweet.id)
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
# Twitter Authentication
auth = tweepy.OAuthHandler("private", "private")
auth.set_access_token("private", "private")
api = tweepy.API(auth)

archive = 'TrumpTweetsArchive.csv'

while True:
    nextTweetTimeList = get_next_tweet_time(archive)
    nextTweetTime = list_to_datetime(nextTweetTimeList)
    print(nextTweetTime)
    print(nextTweetTimeList)
    while True:
        reply_to_people(archive)
        if nextTweetTime < datetime.datetime.now():
            regular_tweet(archive)
            follow_people()
            break
        else:
            time.sleep(300)
