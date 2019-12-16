#!/usr/bin/env python3
import pickle
import sys

from TrainModel import train_model


def main():
    exit_status = 1

    if len(sys.argv) < 2:
        print("Specify one or more commands ('tweet', 'train', or 'update')")
    else:
        command = sys.argv[1]
        if command == 'tweet':
            exit_status = 2  # TODO
        elif command == 'train':
            # TODO make these configurable
            input_file = 'data/trump_tweets.ndjson'
            output_file = 'model.pkl'

            model = train_model(input_file)
            with open(output_file, 'wb') as f:
                pickle.dump(model, f)

            exit_status = 0
        elif command == 'update':
            exit_status = 2  # TODO
        else:
            print('Invalid command')

    exit(exit_status)


if __name__ == '__main__':
    main()
