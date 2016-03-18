#!/usr/bin/python -t
# coding: utf8


import re
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

resp = session.query(CPO.Msg).filter(CPO.Msg.message_id.in_(["<56E67DDA.20000@vipct.ru>",
                                                             "<56D42420.9060000@gmail.com>",
                                                             "<9D619583E62EC54598F189DEDA38004F97D9D9@msk-srv03mbxp.akrikhin.local>"])).all()
train = list()
answer = list()

print len(resp)
for one in resp:
    train.append(one)
    answer.append(one.category)

from sklearn.feature_extraction.text import CountVectorizer

count_vect = CountVectorizer(tokenizer=mytoken, analyzer='word', preprocessor=specfeatures)
X_train_counts = count_vect.fit_transform(resp)

print X_train_counts.shape

from sklearn.feature_extraction.text import TfidfTransformer

tfidf_transformer = TfidfTransformer(use_idf=False)
X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)
print X_train_tfidf.shape

from sklearn.naive_bayes import MultinomialNB

clf = MultinomialNB().fit(X_train_tfidf, X_train_target)


session.close()
