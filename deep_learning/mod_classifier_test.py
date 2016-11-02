#!/usr/bin/python -t
# coding: utf8

"""
Классификация текстов(документов), сообщений и т.д.

1. Содержит модели классификаторов
2. Для каждой модели определены методы загрузки данных из базы, тренировки и извлечения признаков

"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import re
import os
import json
from configuration import *
import objects as CPO
from sqlalchemy import func

import numpy as np
from time import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import Perceptron
from sklearn.naive_bayes import BernoulliNB, MultinomialNB, GaussianNB
from sklearn import svm
from sklearn.model_selection import GridSearchCV
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.externals import joblib


import pymorphy2

morph = pymorphy2.MorphAnalyzer()


class ClassifierNew(object):
    clf = None
    outlier = None
    vectorizer = None
    scaler = None
    debug = False

    def init_and_fit_new(self, debug=False):
        """
        Инициализация классификаторов.
        Создание объектов и тренировка.

        :return:
        """

        session = CPO.Session()
        self.debug = debug

        cats = CPO.GetCategory().keys()

        try:
            resp = session.query(CPO.TrainData.category, func.count(CPO.TrainData.category)).\
                filter(CPO.TrainData.train_epoch != 0).\
                group_by(CPO.TrainData.category).\
                all()
        except Exception as e:
            print(str(e))
            raise e
        else:
            cat_min = 100000
            for cat, count in resp:
                if int(count) < cat_min:
                    cat_min = int(count)
            if cat_min != 0:
                limit = cat_min
                print("Будет сформирована выборка из - {} примеров в каждой категории.".format(cat_min))
            else:
                print("Недостаточно данных для формирования обучающей выборки. В одной из категорий - {} примеров".format(cat_min))
                exit()

            train = list()
            answer = list()

            for current_cat in cats:
                try:
                    count = session.query(CPO.TrainData).\
                        filter(CPO.TrainData.category == current_cat,
                               CPO.TrainData.train_epoch != 0).limit(limit).count()

                    resp = session.query(CPO.TrainData).\
                        filter(CPO.TrainData.category == current_cat,
                               CPO.TrainData.train_epoch != 0).limit(limit)
                    print("Готовим категорию: {} - {} сообщений".format(current_cat, count))
                except Exception as e:
                    print(str(e))
                    session.close()
                    raise e
                else:
                    for one in resp:
                        train.append(one)
                        answer.append(one.category)


        """
        # Загружаем тренировочные данные
        try:
            resp = session.query(CPO.TrainData).filter(CPO.TrainData.train_epoch != 0,
                                                       CPO.TrainData.category == 'normal').all()


            resp = session.query(CPO.TrainData).filter(CPO.TrainData.train_epoch != 0).all()
        except Exception as e:
            print "Error. Mod_classifier_new. Ошибка загрузки данных для тренировки. %s" % str(e)
            raise e
        else:
            if not resp:
                print("# Данных для обучения не найдено.")
                print("# Создаем заглушки для обучения.")
                # Создаем заглушки для обучения
                resp = list()
                cats = CPO.GetCategory().values()
                for i in cats:
                    new = CPO.TrainData()
                    new.message_id = str(i.id)
                    new.message_text = i.category
                    new.category = i.code
                    new.train_epoch = 0
                    resp.append(new)

            # Проводим обучение
            train = list()
            answer = list()
            # Нормальные сообщения тестовые данные
            for one in resp:
                train.append(one)
                answer.append(one.category)
        """

        print "Count Train: %s" % len(train)

        # Готовим векторизатор
        use_hashing = True
        t0 = time()
        if use_hashing:
            #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
            #                               tokenizer=mytoken, preprocessor=specfeatures_new)
            vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=5000,
                                           tokenizer=mytoken, preprocessor=specfeatures_new2)

            X_train = vectorizer.transform(train)
        else:
            vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=STOP_WORDS, analyzer='word',
                                         tokenizer=mytoken, preprocessor=features_extractor2)
            X_train = vectorizer.fit_transform(train)

        self.vectorizer = vectorizer

        if self.debug:
            duration = time() - t0
            print "TRAIN data"
            print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
            print("n_samples: %d, n_features: %d" % X_train.shape)
            print "\n"

        # Создаем классификаторы
        self.clf = list()

        #self.clf.append(Perceptron(n_iter=1000, class_weight="balanced", alpha=1e-06, penalty="l1"))
        #self.clf.append(MLPClassifier(solver='sgd', verbose=True, max_iter=500))
        """
        self.clf.append(
            GridSearchCV(MLPClassifier(solver='lbfgs', verbose=True),
                         param_grid={'alpha': [0.05, 0.01, 0.005, 0.001, 0.0005, 0.0001],
                                     'hidden_layer_sizes': [(500, 500), (1000, 1000), (1000, 500), (300,), (500,)],
                                     'activation': ['identity', 'logistic', 'tanh', 'relu']})
        )
        """
        self.clf.append(
            GridSearchCV(MLPClassifier(solver='lbfgs', verbose=False),
                         param_grid={'alpha': [0.05, 0.01],
                                     'hidden_layer_sizes': [(100,), (300,)],
                                     'activation': ['relu']})
        )

        #self.clf.append(MLPClassifier(solver='lbfgs', verbose=True, hidden_layer_sizes=(1000, 1000), alpha=0.01))
        #self.clf.append(MultinomialNB(alpha=0.1))
        #self.clf.append(BernoulliNB(alpha=0.1, binarize=0.0))
        """
        self.clf.append(
            Pipeline([
                ('feature_selection',SelectFromModel(LinearSVC(penalty="l2", dual=False, tol=1e-3,
                                                               class_weight="balanced"))),
                ('classification', Perceptron(n_iter=50, class_weight="balanced", alpha=1e-06, penalty="l1"))
            ])
        )

        self.clf.append(
            Pipeline([
                ('feature_selection', SelectFromModel(ExtraTreesClassifier(n_estimators=15, random_state=0,
                                                                           class_weight="balanced"))),
                ('classification', LinearSVC(penalty="l2", dual=False, tol=1e-3, class_weight="balanced"))
            ])
        )
        """
        t0 = time()
        # Тренируем классификатор
        for one in self.clf:
            print("Training: {}".format(one))
            one.fit(X_train, answer)
            print("Оценка: ")
            print one.cv_results_['rank_test_score']
            print one.best_params_
            print one.best_score_
        train_time = time() - t0
        if self.debug:
            print("train time: %0.3fs" % train_time)

    def init_and_fit_files(self, debug=False):
        """
        Инициализация классификаторов и тренировка.
        Чтение данных из файлов.

        :return:
        """

        session = CPO.Session()
        self.debug = debug

        cats = CPO.GetCategory().keys()

        train = list()
        answer = list()
        count = 0

        class msg_data(object):
            message_text = ''
            message_title = ''
            category = ''
            in_reply_to = ''
            references = ''
            recipients = ''
            cc_recipients = ''

        for current_cat in ['normal', 'conflict']:
            print("new_train_data/{}/".format(current_cat))
            file_list = list()
            for root, dirs, f_list in os.walk("new_train_data/{}/".format(current_cat)):
                for oo in f_list:
                    if 'class.nfo' != oo:
                        file_list.append('new_train_data/{}/{}'.format(current_cat, oo))

            print("Готовим категорию: {} - {} сообщений".format(current_cat, len(file_list)))

            for ff in file_list:
                f = open(ff, 'r')
                ss = f.read()
                one = json.loads(ss)
                new = msg_data()
                new.message_text = one['message_text']
                new.message_title = one['message_title']
                new.category = one['category']
                new.in_reply_to = one['in_reply_to']
                new.references = one['references']
                new.recipients = one['recipients']
                new.cc_recipients = one['cc_recipients']

                train.append(new)
                answer.append(one['category'])

        print "Count Train: %s" % len(train)

        # Готовим векторизатор
        use_hashing = True
        t0 = time()


        if use_hashing:
            #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
            #                               tokenizer=mytoken, preprocessor=specfeatures_new)
            vectorizer = HashingVectorizer(stop_words=CPO.STOP_WORDS, analyzer='word', non_negative=True, n_features=10000,
                                           tokenizer=mytoken, preprocessor=specfeatures_new2)

            X_train = vectorizer.transform(train)
        else:
            vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=CPO.STOP_WORDS, analyzer='word',
                                         tokenizer=mytoken, preprocessor=CPO.features_extractor2)

            X_train = vectorizer.fit_transform(train)

        scaler = StandardScaler(with_mean=False).fit(X_train)
        X_train = scaler.transform(X_train)

        self.scaler = scaler
        self.vectorizer = vectorizer

        if self.debug:
            duration = time() - t0
            print "TRAIN data"
            print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
            print("n_samples: %d, n_features: %d" % X_train.shape)
            print "\n"

        # Создаем классификаторы
        self.clf = list()

        """
        self.clf.append(MLPClassifier(solver='sgd', verbose=False, max_iter=500))


        self.clf.append(
            GridSearchCV(MLPClassifier(verbose=False),
                         param_grid={'alpha': [0.001, 0.0005, 0.0001, 0.00005, 0.00001, 0.000001],
                                     'hidden_layer_sizes': [(1000, 500), (500, 500), (500, 300), (500, 100), (500,),
                                                            (300,), (100,)],
                                     'activation': ['tanh', 'relu'],
                                     'max_iter': [1000, 2000],
                                     'solver': ['lbfgs', 'sgd']})
        )
        """
        # use_hashing = False
        # {'alpha': 0.0001, 'activation': 'tanh', 'hidden_layer_sizes': (1000, 500)} = score: 0.617486338798
        # {'alpha': 0.001, 'activation': 'relu', 'hidden_layer_sizes': (500, 500)} = 0.612021857923

        # use_hashing = True
        # {'alpha': 0.001, 'activation': 'tanh', 'max_iter': 500, 'solver': 'lbfgs', 'hidden_layer_sizes': (100,)} = 0.672131147541
        # {'alpha': 0.0005, 'activation': 'relu', 'max_iter': 2000, 'solver': 'lbfgs', 'hidden_layer_sizes': (100,)} = 0.672131147541



        """
        self.clf.append(
            GridSearchCV(MLPClassifier(solver='lbfgs', verbose=False),
                         param_grid={'alpha': [0.05, 0.01],
                                     'hidden_layer_sizes': [(100,), (300,)],
                                     'activation': ['relu']})
        )
        """

        #self.clf.append(MLPClassifier(alpha=0.001, activation='tanh', max_iter=500, solver='lbfgs', hidden_layer_sizes=(100,)))
        self.clf.append(MLPClassifier(alpha=0.0001, activation='tanh', max_iter=2000, solver='lbfgs', hidden_layer_sizes=(1000, 500)))
        self.clf.append(MultinomialNB(alpha=0.1))

        # self.clf.append(BernoulliNB(alpha=0.1, binarize=0.0))
        self.clf.append(
            GridSearchCV(
                MultinomialNB(),
                param_grid={'alpha': [0.0, 0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001]}
            )
        )
        # hashing = True, scaling = True
        # {'alpha': 0.1} = 0.644808743169

        self.clf.append(
            GridSearchCV(
                BernoulliNB(binarize=0.0),
                param_grid={'alpha': [0.0, 0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001]}
            )
        )
        # hashing = True, scaling = True
        # {'alpha': 1e-05} = 0.606557377049

        t0 = time()
        # Тренируем классификатор
        for one in self.clf:
            print("Training: {}".format(one))
            one.fit(X_train, answer)
            if isinstance(one, GridSearchCV):
                print("Оценка: ")
                print one.cv_results_['rank_test_score']
                print one.best_params_
                print one.best_score_
        train_time = time() - t0
        if self.debug:
            print("train time: %0.3fs" % train_time)


    def classify_new2(self, data=None, debug=False):
        """
        Классификация образца классификатором.
        Проверка результата классификации детектором аномалий.
        Если детектор и классификатор определяют образец как аномалию (т.е. - conflict), соглашаемся.
        Если детектор считаем аномалией, а классфикатор нет, возращаем результат детектора.

        :return:
        """

        test = [data]
        #X_test = self.vectorizer.transform(test)
        X_test = self.scaler.transform(self.vectorizer.transform(test))

        pred = list()
        complex_pred = dict()
        for one in self.clf:
            p = one.predict(X_test)
            pred.append(p)
            if p[0] in complex_pred.keys():
                complex_pred[p[0]] += 1
            else:
                complex_pred[p[0]] = 1

        if self.debug:
            print("Классификация: {}".format(pred))
            print("Комплексный итог: {}".format(complex_pred))

        for one in complex_pred.keys():
            if complex_pred[one] >= 2:
                return one, "{0}-1:{0}-1:{0}-1".format(one)

        """
        if (float(complex_pred) / 3) > 0.5:
            return "normal", "normal-1:" + "-0.5:".join(pred) + "-0.5"
        else:
            return "conflict", "conflict-1:" + "-0.5:".join(pred) + "-0.5"
        """

    def score(self, test_x=None, test_y=None):

        X_test = self.vectorizer.transform(test_x)

        for one in self.clf:
            print one.score(X_test, test_y)
            if isinstance(one, MLPClassifier):
                print [coef.shape for coef in one.coefs_]

    def dump(self, dir='.'):
        joblib.dump(self.vectorizer, '{}/vectorizer.pkl'.format(dir))
        joblib.dump(self.scaler, '{}/scaler.pkl'.format(dir))
        for i in range(len(self.clf)):
            joblib.dump(self.clf[i], '{}/{}_clf.pkl'.format(dir, i))


def features_extractor(entry):
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
    for s in splitter.split(entry.message_text + entry.message_title):
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

def features_extractor2(entry):
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
    for s in splitter.split(entry.message_text + entry.message_title):
        if (2 < len(s) < 20 and s not in STOP_WORDS) or (s not in STOP_WORDS and s in [u"не", u"ни"]):
            summarywords.append(s)

    # print 'sum words: ',summarywords

    uc = 0
    for i in range(len(summarywords)):
        w = summarywords[i]
        if f.get(w):
            f[w] += 1
        else:
            f[w] = 1

        # Подсчитать количество слов, написанных заглавными буквами
        if w.isupper():
            uc += 1

        # Выделить в качестве признаков пары слов из резюме
        if i < len(summarywords)-1:
            j = i + 1
            word = summarywords[j]
            two_words = ' '.join([w, word])
            # print 'Two words: ',twowords,'\n'
            if f.get(two_words):
                f[two_words] += 1
            else:
                f[two_words] = 1


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
    # print entry.message_text

    # Ищем вопросительные знаки
    quest = find_questions.findall(entry.message_text)
    f['QUESTION'] = len(quest)

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
                # print "NUMBER : ", number.string
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

def specfeatures_new2(entry):
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
    find_questions = re.compile('\?{2,5}', re.UNICODE)
    f = dict()
    results = list()
    # print entry.message_text

    # Ищем вопросительные знаки
    quest = find_questions.findall(entry.message_text)
    f['QUESTION'] = len(quest)

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
            w = titlewords[i]
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
            w = summarywords[i]
            number = find_n.search(w)
            if number:
                # print "NUMBER : ", number.string
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


if __name__ == '__main__':


    session = CPO.Session()
    import requests

    # Инициализация переменных и констант
    try:
        CPO.initial_configuration()
    except Exception as e:
        print "Ошибка чтения настроек CPO.initial_configuration(). %s" % str(e)
        raise e

    # Загружаем тестовые данные
    try:
        resp = session.query(CPO.Msg, CPO.TrainData).\
            join(CPO.TrainData, CPO.Msg.message_id == CPO.TrainData.message_id).\
            filter(CPO.TrainData.train_epoch == 0).limit(100)
    except Exception as e:
        print "Error. Mod_classifier_new. Ошибка загрузки данных для тренировки. %s" % str(e)
        raise e
    else:
        test_x = list()
        test_y = list()
        for one, two in resp:
            test_x.append(one)
            test_y.append(two.category)
            print "\n {} - {}".format(one.message_id,  two.category)
            data = dict()
            data['message_text'] = one.message_text
            data['message_title'] = one.message_title
            data['category'] = one.category
            data['in_reply_to'] = one.in_reply_to
            data['references'] = one.references
            data['recipients'] = one.recipients
            data['cc_recipients'] = one.cc_recipients
            data = json.dumps(data)
            req = requests.post('http://192.168.0.104:8585/api/detect/predict', data={'service': 'test', 'data': data})
            print "{} \n".format(req.text)
            raw_input()

    finally:
        session.close()

    """
    session = CPO.Session()

    # Инициализация переменных и констант
    try:
        CPO.initial_configuration()
    except Exception as e:
        print "Ошибка чтения настроек CPO.initial_configuration(). %s" % str(e)
        raise e

    predictor = ClassifierNew()
    predictor.init_and_fit_files(debug=True)

    # Загружаем тестовые данные
    try:
        resp = session.query(CPO.Msg, CPO.TrainData).\
            join(CPO.TrainData, CPO.Msg.message_id == CPO.TrainData.message_id).\
            filter(CPO.TrainData.train_epoch == 0).limit(100)
    except Exception as e:
        print "Error. Mod_classifier_new. Ошибка загрузки данных для тренировки. %s" % str(e)
        raise e
    else:
        test_x = list()
        test_y = list()
        for one, two in resp:
            test_x.append(one)
            test_y.append(two.category)
            print "\n {} - {}".format(one.message_id,  two.category)
            print "{} \n".format(predictor.classify_new2(data=one))

        predictor.score(test_x, test_y)
        predictor.dump()
    finally:
        session.close()
    """


