import argparse
import json
import logging
import os
import textwrap

import pandas as pd

import bisemantic
from bisemantic import TextualEquivalenceModel, label, text_1, text_2


def main():
    parser = create_argument_parser()
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)-15s %(levelname)-8s %(message)s", level=args.log.upper())
    args.func(args)


def create_argument_parser():
    parser = argparse.ArgumentParser(description=bisemantic.__doc__)
    parser.add_argument('--version', action='version', version="%(prog)s " + bisemantic.__version__)
    parser.add_argument("--log", default="WARNING", help="logging level")
    parser.set_defaults(func=lambda _: parser.print_usage())

    subparsers = parser.add_subparsers(title="Text Pair Equivalence")

    column_renames = argparse.ArgumentParser(add_help=False)
    column_renames.add_argument("--text-1-name", metavar="NAME", help="column containing the first text pair element")
    column_renames.add_argument("--text-2-name", metavar="NAME", help="column containing the second text pair element")
    column_renames.add_argument("--label-name", metavar="NAME", help="column containing the label")

    train_parser = subparsers.add_parser("train", description=textwrap.dedent("""\
    Train a model to predict textual equivalence."""), parents=[column_renames], help="train model")
    train_parser.add_argument("training", type=data_file, help="training data")
    train_parser.add_argument("--validation", type=data_file, help="validation data")
    train_parser.add_argument("--units", type=int, default=128, help="LSTM hidden layer size (default 128)")
    train_parser.add_argument("--epochs", type=int, default=10, help="training epochs (default 10)")
    train_parser.add_argument("--model-directory-name", metavar="MODEL", type=output_directory,
                              help="output model directory")
    train_parser.add_argument("--n", type=int, help="number of training samples to use (default all)")
    train_parser.set_defaults(func=lambda args: train(args))

    predict_parser = subparsers.add_parser("predict", description=textwrap.dedent("""\
    Use a model to predict textual equivalence."""), parents=[column_renames], help="predict equivalence")
    predict_parser.add_argument("model", type=model_directory, help="model directory")
    predict_parser.add_argument("test", type=data_file, help="test data")
    predict_parser.add_argument("--n", type=int, help="number of test samples to use (default all)")
    predict_parser.set_defaults(func=lambda args: predict(args))

    return parser


def train(args):
    training = fix_columns(args.training.head(args.n),
                           text_1_name=args.text_1_name, text_2_name=args.text_2_name, label_name=args.label_name)
    logging.info("Train on %d samples" % len(training))
    model, history = TextualEquivalenceModel.train(training, args.units, args.epochs, args.validation)
    history = history.history
    if args.model_directory_name is not None:
        logging.info("Save model to %s" % args.model_directory_name)
        model.save(model_filename(args.model_directory_name))
        with open(history_filename(args.model_directory_name), mode="w") as f:
            json.dump(history, f, sort_keys=True, indent=4, separators=(',', ': '))
    print("Training\naccuracy=%0.4f, loss=%0.4f" % (history["acc"][-1], history["loss"][-1]))
    if args.validation is not None:
        print("Validation\naccuracy=%0.4f, loss=%0.4f" % (history["val_acc"][-1], history["val_loss"][-1]))


def predict(args):
    test = fix_columns(args.test.head(args.n),
                       text_1_name=args.text_1_name, text_2_name=args.text_2_name, label_name=args.label_name)
    logging.info("Predict labels for %d pairs" % len(test))
    model, _ = args.model
    print(pd.DataFrame({"predicted": model.predict(test)}).to_csv())


def data_file(filename):
    """
    Load a test or training data file.

    A data file is a CSV file. Any rows with null values are dropped.

    :param filename: name of data file
    :type filename: str
    :return: data stored in the data file
    :rtype: pandas.DataFrame
    """
    data = pd.read_csv(filename)
    m = len(data)
    data = data.dropna()
    n = len(data)
    if m != n:
        logging.info("Dropped %d lines with null values from %s" % (m - n, filename))
    return data


def fix_columns(data, text_1_name=text_1, text_2_name=text_2, label_name=label):
    """
    Rename columns in an input data frame to the ones bisemantic expects. Drop unused columns. If an argument is None
    the corresponding column muat already be in the raw data.

    :param data: raw data
    :type data: pandas.DataFrame
    :param text_1_name: name of the text 1 column in the raw data
    :type text_1_name: str
    :param text_2_name: name of the text 2 column in the raw data
    :type text_2_name: str
    :param label_name: name of the label column in the raw data
    :type label_name: str
    :return: data frame containing just the needed columns
    :rtype: pandas.DataFrame
    """
    for name in [text_1_name, text_2_name, label_name]:
        if name is not None:
            if name not in data.columns:
                raise ValueError("Missing column %s" % name)
    data = data.rename(columns={text_1_name: text_1, text_2_name: text_2, label_name: label})
    if label in data.columns:
        columns = [text_1, text_2, label]
    else:
        columns = [text_1, text_2]
    return data[columns]


def output_directory(directory_name):
    os.makedirs(directory_name)
    return directory_name


def model_directory(directory_name):
    model = TextualEquivalenceModel.load(model_filename(directory_name))
    with open(history_filename(directory_name)) as f:
        history = json.load(f)
    return model, history


def model_filename(directory_name):
    return os.path.join(directory_name, "model.h5")


def history_filename(directory_name):
    return os.path.join(directory_name, "history.json")
