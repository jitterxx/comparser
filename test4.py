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
from sklearn.neural_network import BernoulliRBM
from sklearn import linear_model

import pymorphy2
morph = pymorphy2.MorphAnalyzer()

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
    splitter = re.compile('\\W*', re.UNICODE)
    f = {}

    # Извлечь слова из резюме
    summarywords = list()
    for s in splitter.split(entry):
        if (2 < len(s) < 20 and s not in STOP_WORDS) or (s not in STOP_WORDS and s in [u"не", u"ни"]):
            summarywords.append(s)

    # print 'sum words: ',summarywords

    # Подсчитать количество слов, написанных заглавными буквами
    uc = 0
    for i in range(len(summarywords)):
        word = morph.parse(summarywords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
            if f.get(w):
                f[w] += 1
            else:
                f[w] = 1
            if w.isupper():
                uc += 1
            # Выделить в качестве признаков пары слов из резюме
            if i < len(summarywords)-1:
                j = i + 1
                word = morph.parse(summarywords[j])[0]  # Берем первый вариант разбора
                if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
                    # print "Не используем", word.normal_form
                    pass
                else:
                    twowords = ' '.join([w, word.normal_form])
                    # print 'Two words: ',twowords,'\n'
                    if f.get(twowords):
                        f[twowords] += 1
                    else:
                        f[twowords] = 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(summarywords)) and (float(uc)/len(summarywords) > 0.3):
        f['UPPERCASE'] = 1

    #for one in f:
    #    print one
    # raw_input()

    return f


session = CPO.Session()

resp = session.query(CPO.TrainData).filter(CPO.or_((CPO.TrainData.train_epoch == -1),
                                                   (CPO.TrainData.train_epoch == 0),
                                                   (CPO.TrainData.train_epoch == 0))).all()
train = list()
answer = list()

for one in resp:
    train.append(one.message_title + one.message_text)
    answer.append(one.category)

resp = session.query(CPO.TrainData).filter(CPO.or_((CPO.TrainData.train_epoch == 1),
                                                   (CPO.TrainData.train_epoch == 1))).all()
test = list()
test_answer = list()
test_id = list()
for one in resp:
    test.append(one.message_title + one.message_text)
    test_answer.append(one.category)
    test_id.append(one.id)

print "Count Train: %s, Test: %s" % (len(train), len(test))
categories = ["conflict", "normal"]
use_hashing = False


t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                   tokenizer=specfeatures)
    #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, non_negative=True, n_features=60000)

    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.75, stop_words=STOP_WORDS, analyzer='word',
                                 tokenizer=specfeatures, use_idf=True)
    # vectorizer = TfidfVectorizer(max_df=0.75, max_features=5000,                                  use_idf=False, norm="l1")

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
ch2 = SelectKBest(chi2, k=500)
X_train = ch2.fit_transform(X_train, answer)
X_test = ch2.transform(X_test)
duration = time() - t0
print "Select 500 best features: "
print("done in %fs at %0.3f Text/s" % (duration, len(test) / duration))

# Models we will use
logistic = Perceptron(n_iter=50, class_weight="balanced")
rbm = BernoulliRBM(random_state=0, verbose=True)

classifier = Pipeline(steps=[('rbm', rbm), ('logistic', logistic)])

###############################################################################
# Training

# Hyper-parameters. These were set by cross-validation,
# using a GridSearchCV. Here we are not performing cross-validation to
# save time.
rbm.learning_rate = 0.06
rbm.n_iter = 20
# More components tend to give better prediction performance, but larger
# fitting time
rbm.n_components = 100
#logistic.C = 6000.0

# Training RBM-Logistic Pipeline
classifier.fit(X_train, answer)

# Training Logistic regression
logistic_classifier = Perceptron(n_iter=50, class_weight="balanced")
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