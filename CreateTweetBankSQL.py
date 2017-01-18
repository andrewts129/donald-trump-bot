import sqlite3
import json

# This is a json file of every @realDonaldTrump tweet, compiled by TrumpTwitterArchive.com
with open('realdonaldtrump_long.json') as data_file:
    data = json.load(data_file)

db = sqlite3.connect('TrumpTweets.db')
cursor = db.cursor()

# id is the id of every tweet, as assigned by Twitter
cursor.execute('CREATE TABLE tweets(id INTEGER PRIMARY KEY, text TEXT, time TEXT)')
db.commit()

# This is a list of tuples containing all the relevant information about the tweets that will be put into the database
thingsToStore = []

for entry in data:

    # Excludes retweets
    if not hasattr(entry, 'retweeted_status'):
        tweetID = entry['id']
        text = entry['text']
        time = entry['created_at']

        # Sometimes retweets manage to get past the last if. This checks again.
        if 'RT @' not in text and '"@' not in text:
            thing = (tweetID, text, time)
            thingsToStore.append(thing)

# Places all of the tuples into the database
cursor.executemany('INSERT INTO tweets(id, text, time) VALUES(?,?,?)', thingsToStore)
db.commit()

db.close()
