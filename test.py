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
    f = results = dict()

    # Извлечь и аннотировать слова из заголовка
    titlewords = list()
    for s in splitter.split(entry.message_title):
        if 2 <= len(s) < 20 and s not in STOP_WORDS:
            titlewords.append(s)

    uc = 0
    for i in range(len(titlewords)):
        word = morph.parse(titlewords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
            results.append(w)
            if f.get(w):
                f["title:" + w] += 1
            else:
                f["title:" + w] = 1
            if w.isupper():
                uc += 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(titlewords)) and (float(uc)/len(titlewords) > 0.1):
        f["title:UPPERCASE"] = 1

    # Извлечь слова из резюме
    summarywords = list()
    for s in splitter.split(entry.message_text):
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
            results.append(w)
            if f.get(w):
                f[w] += 1
            else:
                f[w] = 1
            if w.isupper():
                uc += 1
            # Выделить в качестве признаков пары слов из резюме

    for i in range(len(results) - 1):
        twowords = ' '.join([results[i], results[i + 1]])
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

def specfeatures_new(entry):
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
    find_n = re.compile('\d+', re.UNICODE)
    find_questions = re.compile('\?{1,5}', re.UNICODE)
    f = dict()
    results = list()
    print entry.message_text

    # Ищем вопросительные знаки
    quest = find_questions.findall(entry.message_text)
    if quest:
        print "QUESTION : ", quest
        if f.get("QUESTION"):
            f['QUESTION'] += 1
        else:
            f['QUESTION'] = 1

    # Извлечь и аннотировать слова из заголовка
    titlewords = list()
    for s in splitter.split(entry.message_title):
        if 2 <= len(s) < 20 and s not in STOP_WORDS:
            titlewords.append(s)

    uc = 0
    for i in range(len(titlewords)):
        word = morph.parse(titlewords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
            results.append(w)
            if f.get(w):
                f["title:" + w] += 1
            else:
                f["title:" + w] = 1
            if w.isupper():
                uc += 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(titlewords)) and (float(uc)/len(titlewords) > 0.1):
        f["title:UPPERCASE"] = 1

    # Извлечь слова из резюме
    summarywords = list()
    for s in splitter.split(entry.message_text):
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
            number = find_n.search(w)
            if number:
                print "NUMBER : ", number.string
                if f.get("NUMBER"):
                    f['NUMBER'] += 1
                else:
                    f['NUMBER'] = 1
            else:
                results.append(w)
                if f.get(w):
                    f[w] += 1
                else:
                    f[w] = 1
                if w.isupper():
                    uc += 1

    # Выделить в качестве признаков пары слов из резюме
    for i in range(len(results) - 1):
        twowords = ' '.join([results[i], results[i + 1]])
        # print 'Two words: ',twowords,'\n'
        if f.get(twowords):
            f[twowords] += 1
        else:
            f[twowords] = 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(summarywords)) and (float(uc)/len(summarywords) > 0.3):
        f['UPPERCASE'] = 1

    # Несколько адресатов или один
    count = 0
    if entry.recipients != "empty" and entry.recipients:
        s = re.split(":", entry.recipients)
        count = len(s)

    if entry.cc_recipients != "empty" and entry.cc_recipients:
        s = re.split(":", entry.cc_recipients)
        count += len(s)

    if count > 1:
        f["MANYRECIPIENTS"] = 1
    else:
        f["MANYRECIPIENTS"] = 0

    # Сколкьо сообщений в цепочке
    count = 0
    if entry.references:
        s = re.split(" ", entry.references)
        count = len(s)

    if count > 3:
        f["MANYREPLY"] = 1
    else:
        f["MANYREPLY"] = 0

    #for one in f.keys():
    #    print one, " : ", f[one]

    #print "*" * 30
    #raw_input()

    return f

def mytoken(entry):

    return entry


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

#test = train
#test_answer = answer

print "Count Train: %s, Test: %s" % (len(train), len(test))
categories = ["conflict", "normal"]
use_hashing = True


t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                   tokenizer=mytoken, preprocessor=specfeatures_new)
    #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, non_negative=True, n_features=60000)

    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, stop_words=STOP_WORDS, analyzer='word',
                                 tokenizer=mytoken, preprocessor=specfeatures_new, use_idf=True, norm="l1")
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

if use_hashing:
    feature_names = None
else:
    feature_names = vectorizer.get_feature_names()

select_chi2 = 0
if select_chi2:
    print("Extracting %d best features by a chi-squared test" % select_chi2)
    t0 = time()
    ch2 = SelectKBest(chi2, k=select_chi2)
    X_train = ch2.fit_transform(X_train, answer)
    X_test = ch2.transform(X_test)
    if feature_names:
        # keep selected feature names
        feature_names = [feature_names[i] for i
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
    return clf_descr, score, train_time, test_time, pred

from sklearn.svm import SVC

results = []
for clf, name in (
        #(RidgeClassifier(tol=1e-2, solver="sag"), "Ridge Classifier"),
        (Perceptron(n_iter=50, class_weight="balanced", alpha=1e-06, penalty="l2"), "Perceptron"),
        #(PassiveAggressiveClassifier(n_iter=50), "Passive-Aggressive"),
        (SVC(C=0.01, kernel="rbf", class_weight="balanced"), "SVC"),
        #(KNeighborsClassifier(n_neighbors=5, algorithm="ball_tree"), "kNN"),
        # (RandomForestClassifier(n_estimators=10), "Random forest"),

    ):

    print('=' * 80)
    print(name)
    results.append(benchmark(clf))

for penalty in ["l2", "l1"]:
    continue
    print('=' * 80)
    print("%s penalty" % penalty.upper())
    # Train Liblinear model
    results.append(benchmark(LinearSVC(loss='squared_hinge', penalty=penalty, class_weight="balanced",
                                            dual=False, tol=1e-3)))

    # Train SGD model
    #results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
    #                                       penalty=penalty)))

# Train SGD with Elastic Net penalty
#print('=' * 80)
#print("Elastic-Net penalty")
#results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
#                                       penalty="elasticnet")))

print('=' * 80)
print("SGD")
results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=70, penalty="l2", loss="squared_hinge",
                                       class_weight="balanced")))


# Train NearestCentroid without threshold
#print('=' * 80)
#print("NearestCentroid (aka Rocchio classifier)")
#results.append(benchmark(NearestCentroid()))

# Train sparse Naive Bayes classifiers
print('=' * 80)
print("Naive Bayes")
results.append(benchmark(MultinomialNB(alpha=.01)))
results.append(benchmark(BernoulliNB(alpha=.01)))

#for i in range(0, len(results[0][4])):
#    if results[0][4][i] != results[1][4][i]:
#        print test_id[i], "-", results[0][4][i], " : ", results[1][4][i], " - ", test_answer[i]

#print('=' * 80)
#print("LinearSVC with L1-based feature selection")
# The smaller C, the stronger the regularization.
# The more regularization, the more sparsity.
#results.append(benchmark(Pipeline([
#  ('feature_selection', LinearSVC(penalty="l1", dual=False, tol=1e-3)),
#  ('classification', LinearSVC(class_weight="balanced"))
#])))


for i in range(0, len(test)):
    if test_answer[i] == "conflict":
        print test_id[i], " - ", test_answer[i]
        for j in range(0, len(results)):
            print "\t", results[j][4][i]

session.close()