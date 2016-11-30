import requests
import pandas as pd

# Doesn't look like Trump was actually running his own Twitter until mid-2011 or so
years = ['2012', '2013', '2014', '2015', '2016']

data = []

for year in years:
    url = 'http://trumptwitterarchive.com/data/' + year + '.json'
    r = requests.get(url)
    rawJson = r.json()

    for i in rawJson:
        text = i['text']
        tweetID = i['id_str']
        rawTime = i['created_at']
        time = rawTime[11:16]
        if 'RT @' and '"@' not in text:
            tweet = {'id': tweetID, 'text': text, 'time': time}
            data.append(tweet)


print(data)
df = pd.DataFrame(data)
df.to_csv('TrumpTweetsArchiveTest2.csv')
