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
                    f[twowords] = 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(summarywords)) and (float(uc)/len(summarywords) > 0.3):
        f['UPPERCASE'] = 1

    #for one in f:
    #    print one
    # raw_input()

    return f


session = CPO.Session()

# Нормальные сообщения тренировочные данные
resp = session.query(CPO.TrainData).filter(CPO.and_(CPO.or_((CPO.TrainData.train_epoch == -1),
                                                   (CPO.TrainData.train_epoch == 0)),
                                                   (CPO.TrainData.category == "normal"))).all()
train = list()
answer = list()

# Нормальные сообщения тестовые данные
for one in resp:
    train.append(one.message_title + one.message_text)
    answer.append(one.category)

resp = session.query(CPO.TrainData).filter(CPO.and_(CPO.or_((CPO.TrainData.train_epoch == 1),
                                                   (CPO.TrainData.train_epoch == 1)),
                                                   (CPO.TrainData.category == "normal"))).all()

test = list()
test_answer = list()
test_id = list()
for one in resp:
    test.append(one.message_title + one.message_text)
    test_answer.append(one.category)
    test_id.append(one.id)

# Обучение на всех даных
train2 = train + test

# Аномалии, тестовые данные
resp = session.query(CPO.TrainData).filter(CPO.TrainData.category == "conflict").all()
test_con = list()
test_con_answer = list()
test_con_id = list()
for one in resp:
    test_con.append(one.message_title + one.message_text)
    test_con_answer.append(one.category)
    test_con_id.append(one.id)

print "Count Train: %s, Test: %s, Anomaly: %s" % (len(train), len(test), len(test_con))
categories = ["conflict", "normal"]
use_hashing = False


t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                   tokenizer=specfeatures)
    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=STOP_WORDS, analyzer='word',
                                 tokenizer=specfeatures)
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

import numpy as np
from sklearn import svm

# fit the model
clf = svm.OneClassSVM(nu=0.5, kernel="rbf", gamma=0.1)
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