# donald-trump-bot
Twitter bot that uses President Trump's Twitter account to create Markov chains that imitate him.  
  
The main script, DonaldTrumBot.py, is scheduled to run every ten minutes on Heroku. Most times it will exit without doing anything, but about ~2-3 times a day it will create a tweet and post it.

The secondary script, WordBankCreator.py, sifts through Trump's tweets and comes up with the probabilities of certain words following other words and uploads the results to Google Drive for the main script to download and use. I run this script periodically by hand on my own machine.  
  
The only reason these two scripts are separated is because WordBankCreator.py uses the NLP module spacy to get the parts of speeches in tweets. Simply loading this module uses up about 1GB of RAM, while the free Heroku dyno this bot runs on is limited to about 500MB. So for now, I need to keep that part of the process out of the cloud.
