#!/usr/bin/python -t
# coding: utf8


import mailbox
import email.parser, email.utils
import chardet
from email.header import decode_header
import poplib, email
import base64
import re
# import html2text
import datetime
from dateutil.parser import *
import argparse
from configuration import *
import objects as CPO

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

import sys
reload(sys)
sys.setdefaultencoding("utf-8")


def specfeatures(entry):
    """ Функция для получения признаков(features) из текста
    Выделяет следующие признаки:
    1. email отправителя
    2. email получателей
    3. Слова из темы сообщения
    4. Все пары слов из темы сообщения
    5. Определенные сочетания из темы сообщения
    6. Слова из текста
    7. Все пары слов из текста
    8. Определенные пары слов из текста (specwords)
    9. Оригинальное время создания сообщения, только HH:MM\

    """
    splitter=re.compile('\\W*',re.UNICODE)
    f = {}

    # Извлечь слова из резюме
    summarywords=[s for s in splitter.split(entry)
                  if len(s)>2 and len(s)<20 and s not in STOP_WORDS]
    # print 'sum words: ',summarywords

    # Подсчитать количество слов, написанных заглавными буквами
    uc = 0
    for i in range(len(summarywords)):
        w=summarywords[i]
        f[w]=1
        if w.isupper(): uc += 1
        # Выделить в качестве признаков пары слов из резюме
        if i<len(summarywords)-1:
            j = i+1
            l = [summarywords[i],summarywords[j]]
            twowords = ' '.join(l)
            # print 'Two words: ',twowords,'\n'
            f[twowords]=1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(summarywords)) and (float(uc)/len(summarywords) > 0.3): f['UPPERCASE'] = 1

    return f


use_hashing = True

session = CPO.Session()

resp = session.query(CPO.TrainData).filter(CPO.TrainData.train_epoch == 0).all()
train = list()
answer = list()

for one in resp:
    train.append(one.message_title + one.message_text)
    answer.append(one.category)

resp = session.query(CPO.TrainData).filter(CPO.TrainData.train_epoch == 1).all()
test = list()
test_answer = list()
for one in resp:
    test.append(one.message_title + one.message_text)
    test_answer.append(one.category)

print len(train), len(test)
categories = ["conflict", "normal"]

t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=2 ** 16,
                                   tokenizer=specfeatures)
    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, stop_words=STOP_WORDS)
    X_train = vectorizer.fit_transform(train)

duration = time() - t0
print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
print("n_samples: %d, n_features: %d" % X_train.shape)
print()

print("Extracting features from the test data using the same vectorizer")
t0 = time()
X_test = vectorizer.transform(test)
duration = time() - t0
print("done in %fs at %0.3f Text/s" % (duration, len(test) / duration))
print("n_samples: %d, n_features: %d" % X_test.shape)
print()

if use_hashing:
    feature_names = None
else:
    feature_names = vectorizer.get_feature_names()

select_chi2 = 10
if select_chi2:
    print("Extracting %d best features by a chi-squared test" % select_chi2)
    t0 = time()
    ch2 = SelectKBest(chi2, k=select_chi2)
    X_train = ch2.fit_transform(X_train, answer)
    X_test = ch2.transform(X_test)
    if feature_names:
        # keep selected feature names
        feature_names_2 = [feature_names[i] for i
                           in ch2.get_support(indices=True)]
    print("done in %fs" % (time() - t0))
    print ""

if feature_names:
    feature_names = np.asarray(feature_names)


def trim(s):
    """Trim string to fit on terminal (assuming 80-column display)"""
    return s if len(s) <= 80 else s[:77] + "..."


# Benchmark classifiers
def benchmark(clf):
    print('_' * 80)
    print("Training: ")
    print(clf)
    t0 = time()
    clf.fit(X_train, answer)
    train_time = time() - t0
    print("train time: %0.3fs" % train_time)

    t0 = time()
    pred = clf.predict(X_test)
    test_time = time() - t0
    print("test time:  %0.3fs" % test_time)

    score = metrics.accuracy_score(test_answer, pred)
    print("accuracy:   %0.3f" % score)

    if hasattr(clf, 'coef_'):
        print("dimensionality: %d" % clf.coef_.shape[1])
        print("density: %f" % density(clf.coef_))

        if False and feature_names is not None:
            print("top 10 keywords per class:")
            for i, category in enumerate(categories):
                top10 = np.argsort(clf.coef_[i])[-10:]
                print(trim("%s: %s"
                      % (category, " ".join(feature_names[top10]))))
        print ""

    print("classification report:")
    print(metrics.classification_report(test_answer, pred, target_names=categories))

    print("confusion matrix:")
    print(metrics.confusion_matrix(test_answer, pred))

    print()
    clf_descr = str(clf).split('(')[0]

    raw_input()
    return clf_descr, score, train_time, test_time


results = []
for clf, name in ((Perceptron(n_iter=70), "Perceptron"),):
        #(RidgeClassifier(tol=1e-2, solver="lsqr"), "Ridge Classifier"),
        #(Perceptron(n_iter=50), "Perceptron"),
        #(PassiveAggressiveClassifier(n_iter=50), "Passive-Aggressive"),
        #(KNeighborsClassifier(n_neighbors=10), "kNN"),
        #(RandomForestClassifier(n_estimators=100), "Random forest")):

    print('=' * 80)
    print(name)
    results.append(benchmark(clf))

for penalty in ["l2", "l1"]:
    continue
    print('=' * 80)
    print("%s penalty" % penalty.upper())
    # Train Liblinear model
    results.append(benchmark(LinearSVC(loss='l2', penalty=penalty,
                                            dual=False, tol=1e-3)))

    # Train SGD model
    results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
                                           penalty=penalty)))

# Train SGD with Elastic Net penalty
#print('=' * 80)
#print("Elastic-Net penalty")
#results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
#                                       penalty="elasticnet")))

# Train NearestCentroid without threshold
#print('=' * 80)
#print("NearestCentroid (aka Rocchio classifier)")
#results.append(benchmark(NearestCentroid()))

# Train sparse Naive Bayes classifiers
print('=' * 80)
print("Naive Bayes")
results.append(benchmark(MultinomialNB(alpha=.01)))
results.append(benchmark(BernoulliNB(alpha=.01)))

#print('=' * 80)
#print("LinearSVC with L1-based feature selection")
# The smaller C, the stronger the regularization.
# The more regularization, the more sparsity.
#results.append(benchmark(Pipeline([
#  ('feature_selection', LinearSVC(penalty="l1", dual=False, tol=1e-3)),
#  ('classification', LinearSVC())
#])))


session.close()