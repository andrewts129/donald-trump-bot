import csv
import random

with open('TrumpTweets.csv', 'r') as f:
    reader = csv.reader(f)
    tweets = list(reader)

wordBank = []

for tweet in tweets:
    words = tweet[0].split()

    beforeWord = ""

    for word in words:
        beforeAndCurrent = {'before': beforeWord, 'current': word}
        beforeWord = word
        wordBank.append(beforeAndCurrent)

isFirst = False
firstWord = ''
output = []

while firstWord == '':
    r = random.choice(wordBank)

    if r['before'] == '':
        firstWord = r['current']
        output.append(firstWord)

outputString = ' '.join(output)
lastWordIsEnder = False

while (len(outputString) < 130) & (lastWordIsEnder == False):
    newWord = ''

    while newWord == '':
        r = random.choice(wordBank)
        if r['before'] == output[-1]:
            newWord = r['current']
            output.append(newWord)

    outputString = ' '.join(output)
    print(outputString)
    if (outputString[-1] == '.' or outputString[-1] == '!') and len(outputString) > 90:
        lastWordIsEnder = True

print(outputString)