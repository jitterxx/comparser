#!/usr/bin/python -t
# coding: utf8
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['/home/sergey/dev/conflict analyser'])

import objects as CPO
from configuration import *

import numpy as np
from time import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.feature_selection import SelectFromModel
from sklearn.linear_model import RidgeClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn import svm
from sklearn.linear_model import SGDClassifier
from sklearn.linear_model import Perceptron
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neighbors import NearestCentroid
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.utils.extmath import density
from sklearn import metrics
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.grid_search import GridSearchCV
from sklearn.pipeline import Pipeline, make_pipeline

from pprint import pprint
from time import time
import logging

import test_func

import pymorphy2
morph = pymorphy2.MorphAnalyzer()

session = CPO.Session()

resp = session.query(CPO.TrainData).filter(CPO.or_((CPO.TrainData.train_epoch == -1),
                                                   (CPO.TrainData.train_epoch == 0),
                                                   (CPO.TrainData.train_epoch == 1))).all()
train = list()
answer = list()

for one in resp:
    train.append(one)
    answer.append(one.category)

resp = session.query(CPO.UserTrainData).all()
test = list()
test_answer = list()
test_id = list()
for one in resp:
    clear = session.query(CPO.Msg).filter(CPO.Msg.message_id == one.message_id).one_or_none()
    if clear:
        test.append(clear)
    else:
        test.append(one)
    test_answer.append(one.category)
    test_id.append(one.id)

print("Count Train: %s, Test: %s" % (len(train), len(test)))
categories = ["conflict", "normal"]


# Display progress logs on stdout
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# define a pipeline combining a text feature extractor with a simple
# classifier
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('clf', svm.SVC()),
])
# uncommenting more parameters will give better exploring power but will
# increase processing time in a combinatorial way
parameters = {
    'tfidf__max_df': (0.5, 0.75, 1.0),
    'tfidf__max_features': (100, 500, 1000, 5000, 10000),
    # 'vect__ngram_range': ((1, 1), (1, 2)),  # unigrams or bigrams
    'tfidf__use_idf': (True, False),
    'tfidf__norm': (None, 'l1', 'l2'),
    "tfidf__tokenizer": (None, test_func.specfeatures),
    # 'clf__alpha': (0.01, 0.001, 0.0001, 0.00001, 0.000001, 0.000001),
    'clf__C': (0.01, 0.1, 0.5, 1),
    'clf__kernel': ("rbf", "sigmoid", "poly"),
    # 'clf__penalty': ('l2', 'elasticnet'),
    # 'clf__n_iter': (50, 100, 150),
    'clf__class_weight': ("balanced",),
}

vect = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word',
                         tokenizer=test_func.mytoken, preprocessor=test_func.specfeatures_new)

clf = LinearSVC()
estimators = [("vec", HashingVectorizer()),
              ("clf", LinearSVC())]
pipeline2 = Pipeline(estimators)

parameters2 = {
    "vec__tokenizer": (test_func.mytoken, ),
    "vec__preprocessor": (test_func.specfeatures_new, ),
    "vec__analyzer": (["word"]),
    'clf__C': (0.01, 1),
    'clf__dual': (True, False),
    'clf__loss': (["squared_hinge"]),
    'clf__penalty': ('l2', 'l1'),
    'clf__max_iter': ([100]),
    'clf__class_weight': (["balanced"]),
}

if __name__ == "__main__":
    # multiprocessing requires the fork to happen in a __main__ protected
    # block

    # find the best parameters for both the feature extraction and the
    # classifier
    grid_search = GridSearchCV(pipeline2, parameters2, n_jobs=-1, verbose=1)

    print("Performing grid search...")
    print("pipeline:", [name for name, _ in pipeline2.steps])
    print("parameters:")
    pprint(parameters2)
    t0 = time()
    grid_search.fit(train, answer)
    grid_search.predict(test)
    print("done in %0.3fs" % (time() - t0))
    print()

    print("Best score: %0.3f" % grid_search.best_score_)
    print("Best parameters set:")
    best_parameters = grid_search.best_estimator_.get_params()
    for param_name in sorted(parameters2.keys()):
        print("\t%s: %r" % (param_name, best_parameters[param_name]))


session.close()