#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['/home/sergey/dev/conflict analyser'])

from configuration import *
import objects as CPO

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
import numpy as np
from sklearn import svm
import test_func

import pymorphy2
morph = pymorphy2.MorphAnalyzer()

session = CPO.Session()

# Нормальные сообщения тренировочные данные
resp = session.query(CPO.TrainData).filter(CPO.and_(CPO.or_((CPO.TrainData.train_epoch == -1),
                                                   (CPO.TrainData.train_epoch == 0)),
                                                   (CPO.TrainData.category == "normal"))).all()
train = list()
answer = list()

# Нормальные сообщения тестовые данные
for one in resp:
    train.append(one)
    answer.append(one.category)

resp = session.query(CPO.TrainData).filter(CPO.and_(CPO.or_((CPO.TrainData.train_epoch == 1),
                                                   (CPO.TrainData.train_epoch == 1)),
                                                   (CPO.TrainData.category == "normal"))).all()

test = list()
test_answer = list()
test_id = list()
for one in resp:
    test.append(one)
    test_answer.append(one.category)
    test_id.append(one.id)

# Обучение на всех даных
train2 = train + test

# Аномалии, тестовые данные
resp = session.query(CPO.UserTrainData).filter(CPO.UserTrainData.category == "conflict").all()
test_con = list()
test_con_answer = list()
test_con_id = list()
for one in resp:
    clear = session.query(CPO.Msg).filter(CPO.Msg.message_id == one.message_id).one_or_none()
    if clear:
        test_con.append(clear)
    else:
        test_con.append(one)
    test_con_answer.append(one.category)
    test_con_id.append(one.id)

print "Count Train: %s, Test: %s, Anomaly: %s" % (len(train), len(test), len(test_con))
categories = ["conflict", "normal"]
use_hashing = True


t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                   tokenizer=test_func.mytoken, preprocessor=test_func.specfeatures_new)
    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=STOP_WORDS, analyzer='word',
                                 tokenizer=test_func.mytoken, preprocessor=test_func.specfeatures_new)
    X_train = vectorizer.fit_transform(train)

duration = time() - t0
print "TRAIN"
print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
print("n_samples: %d, n_features: %d" % X_train.shape)
print ""

print("Extracting features from the test data using the same vectorizer")
t0 = time()
X_train2 = vectorizer.transform(train2)
duration = time() - t0
print "TEST"
print("done in %fs at %0.3f Text/s" % (duration, len(train2) / duration))
print("n_samples: %d, n_features: %d" % X_train2.shape)
print ""

print("Extracting features from the test data using the same vectorizer")
t0 = time()
X_test = vectorizer.transform(test)
duration = time() - t0
print "TEST"
print("done in %fs at %0.3f Text/s" % (duration, len(test) / duration))
print("n_samples: %d, n_features: %d" % X_test.shape)
print ""

print("Extracting features from the anomaly data using the same vectorizer")
t0 = time()
X_test_con = vectorizer.transform(test_con)
duration = time() - t0
print "TEST"
print("done in %fs at %0.3f Text/s" % (duration, len(test_con) / duration))
print("n_samples: %d, n_features: %d" % X_test_con.shape)
print ""

if use_hashing:
    feature_names = None
else:
    feature_names = vectorizer.get_feature_names()

# fit the model
clf = svm.OneClassSVM(nu=0.3, kernel="rbf", gamma=0.1)
clf.fit(X_train2)
y_pred_train = clf.predict(X_train)
y_pred_test = clf.predict(X_test)
y_pred_outliers = clf.predict(X_test_con)
n_error_train = y_pred_train[y_pred_train == -1].size
n_error_test = y_pred_test[y_pred_test == -1].size
n_error_outliers = y_pred_outliers[y_pred_outliers == 1].size

print "Ошибки при работе с данными обучения: %s" % n_error_train
print "Ошибки при работе с данными тестов: %s" % n_error_test
print "Ошибки при работе с данными аномалий: %s" % n_error_outliers

for i in range(0, len(test_con)):
    pass
    print test_con_id[i], y_pred_outliers[i], test_con_answer[i]
    raw_input()

session.close()