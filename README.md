# @DonaldTrumBot

Twitter bot that uses President Trump's Twitter account to create Markov chains that imitate him. Account can be found
running live [here](https://twitter.com/DonaldTrumBot).

This program currently runs on my DigitalOcean box:  
* Every night at midnight, it downloads new tweets from [trumptwitterarchive.com](http://www.trumptwitterarchive.com/)
and uses them to train the Markov chain model.  
* Every five minutes, the tweeting script is run. Most of the time, the script will terminate without doing anything.
However, there is a small random chance that it will create a tweet using the model and post it to Twitter. It's
configured to post about 2.5 times a day, on average.

TODO:
* Logging
* CI/CD
* More configuration options (lots of hardcoding right now)
* Experiment with using a neural network model instead of plain Markov chains