import requests
import pandas as pd

years = ['2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016']

data = []

for year in years:
    url = 'http://trumptwitterarchive.com/data/' + year + '.json'
    r = requests.get(url)
    rawJson = r.json()

    for i in rawJson:
        text = i['text']
        id = i['id_str']
        if 'RT @' and '"@' not in text:
            fuck = {'id': id, 'text': text}
            data.append(fuck)


print(data)
df = pd.DataFrame(data)
df.to_csv('TrumpTweetsArchive.csv')


