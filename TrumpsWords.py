import csv
import random
import tweepy


def create_word_bank(source):

    with open(source, 'r') as f:
        reader = csv.reader(f)
        tweets = list(reader)

    word_bank = []

    for tweet in tweets:
        words = tweet[0].split()

        before_word = ""

        for word in words:
            before_and_current = {'before': before_word, 'current': word}
            before_word = word
            word_bank.append(before_and_current)

    return word_bank


def create_tweet(wordBank):

    firstWord = ''
    outputList = []

    while firstWord == '':
        r = random.choice(wordBank)

        if r['before'] == '' and r['current'][0] != '"':
            firstWord = r['current']
            outputList.append(firstWord)

    outputString = ' '.join(outputList)
    lastWordIsEnder = False

    while (len(outputString) < 130) and (lastWordIsEnder == False):
        newWord = ''

        while newWord == '':
            r = random.choice(wordBank)
            if r['before'] == outputList[-1]:
                newWord = r['current']
                outputList.append(newWord)

        outputString = ' '.join(outputList)
        print(outputList)
        if ((outputList[-1][-1] == '.' or outputList[-1][-1] == '!') and len(outputString) > 90) or ('https' in newWord):
            lastWordIsEnder = True

    return outputList


def post_tweet(tweet):
    tweetString = ' '.join(tweet)
    api.update_status(tweetString)


auth = tweepy.OAuthHandler("private", "private")
auth.set_access_token("private", "private")
api = tweepy.API(auth)

wordBank = create_word_bank('TrumpTweets.csv')

tweet = create_tweet(wordBank)

# If the tweet is over 140 characters, try again
while len(' '.join(tweet)) > 140:
    tweet = create_tweet(wordBank)

print(' '.join(tweet))

post_tweet(tweet)
