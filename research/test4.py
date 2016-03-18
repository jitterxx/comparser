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
from sklearn.linear_model import RidgeClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.linear_model import SGDClassifier
from sklearn.linear_model import Perceptron
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neighbors import NearestCentroid
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.extmath import density
from sklearn import metrics
from sklearn.neural_network import BernoulliRBM
from sklearn import linear_model
from sklearn.feature_selection import SelectFromModel
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

print "Count Train: %s, Test: %s" % (len(train), len(test))
categories = ["conflict", "normal"]
use_hashing = False


t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                   tokenizer=test_func.mytoken, preprocessor=test_func.specfeatures_new)
    #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, non_negative=True, n_features=60000)

    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, stop_words=STOP_WORDS, analyzer='word',
                                 tokenizer=test_func.mytoken, preprocessor=test_func.specfeatures_new,
                                 use_idf=True, norm="l1")
    # vectorizer = TfidfVectorizer(max_df=0.75, max_features=5000, use_idf=False, norm="l1")

    X_train = vectorizer.fit_transform(train)

duration = time() - t0
print "TRAIN"
print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
print("n_samples: %d, n_features: %d" % X_train.shape)
print()

print("Extracting features from the test data using the same vectorizer")
t0 = time()
X_test = vectorizer.transform(test)
duration = time() - t0
print "TEST"
print("done in %fs at %0.3f Text/s" % (duration, len(test) / duration))
print("n_samples: %d, n_features: %d" % X_test.shape)
print()


t0 = time()
# ch2 = SelectKBest(chi2, k=500)
# X_train = ch2.fit_transform(X_train, answer)
# X_test = ch2.transform(X_test)
# duration = time() - t0
# print "Select 500 best features: "
# print("done in %fs at %0.3f Text/s" % (duration, len(test) / duration))

# Models we will use
logistic = Perceptron(n_iter=50, class_weight="balanced", alpha=1e-06, penalty="l2")
rbm = BernoulliRBM(random_state=0, verbose=True)

classifier = Pipeline(steps=[('rbm', rbm), ('logistic', logistic)])

###############################################################################
# Training

# Hyper-parameters. These were set by cross-validation,
# using a GridSearchCV. Here we are not performing cross-validation to
# save time.
rbm.learning_rate = 0.06
rbm.n_iter = 5
# More components tend to give better prediction performance, but larger
# fitting time
rbm.n_components = 500
#logistic.C = 6000.0

# Training RBM-Logistic Pipeline
classifier.fit(X_train, answer)

# Training Logistic regression
logistic_classifier = Perceptron(n_iter=50, class_weight="balanced", alpha=1e-06, penalty="l2")
logistic_classifier.fit(X_train, answer)

###############################################################################
# Evaluation

print()
print("Logistic regression using RBM features:\n%s\n" % (
    metrics.classification_report(
        test_answer,
        classifier.predict(X_test))))

print("Perceptron regression using raw features:\n%s\n" % (
    metrics.classification_report(
        test_answer,
        logistic_classifier.predict(X_test))))







session.close()