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

def specfeatures_t2(entry):

    tt = ""

    tt += entry.message_title + "\n"
    tt += entry.message_text + "\n"

    return tt


def tokenizer_t2(entry):

    # print entry

    splitter = re.compile('\\W*', re.UNICODE)
    find_n = re.compile('\d+', re.UNICODE)
    f = dict()

    result = splitter.split(entry)

    for i in range(0, len(result) - 1):
        one = result[i].lower()

        #number = find_n.search(one)

        #if number:
        #    break

        # print one
        if f.get(one):
            f[one] += 1
        else:
            f[one] = 1

        pair = '{} {}'.format(result[i].lower(), result[i + 1].lower())
        # print pair
        if f.get(pair):
            f[pair] += 1
        else:
            f[pair] = 1

    # for a, b in f.iteritems():
    #   print a, " - ", b

    # raw_input()

    return f


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
        use_hashing = False
        t0 = time()


        if use_hashing:
            #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
            #                               tokenizer=mytoken, preprocessor=specfeatures_new)
            vectorizer = HashingVectorizer(stop_words=CPO.STOP_WORDS, analyzer='word', non_negative=True, n_features=10000,
                                           tokenizer=CPO.mytoken, preprocessor=CPO.specfeatures_new2,
                                           norm='l1')
            vectorizer = HashingVectorizer(analyzer='word', n_features=10000, non_negative=True, norm='l1',
                                           tokenizer=CPO.mytoken, preprocessor=CPO.specfeatures_new2)

            vectorizer = HashingVectorizer(analyzer='char', n_features=10000, non_negative=True, norm='l1',
                                           preprocessor=specfeatures_t2)


            X_train = vectorizer.transform(train)
        else:
            vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=CPO.STOP_WORDS, analyzer='word',
                                         tokenizer=CPO.mytoken, preprocessor=CPO.features_extractor2)

            vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words=CPO.STOP_WORDS, analyzer='word',
                                         preprocessor=specfeatures_t2, lowercase=True, norm='l1',
                                         max_df=0.5, min_df=0.02)

            vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words=CPO.STOP_WORDS, analyzer='word',
                                         preprocessor=specfeatures_t2, lowercase=True, norm='l1',
                                         max_df=0.5, min_df=0.01,
                                         tokenizer=tokenizer_t2)

            #vectorizer = TfidfVectorizer(analyzer='char',
            #                             preprocessor=specfeatures_t2, ngram_range=(3, 5), max_features=10000)

            X_train = vectorizer.fit_transform(train)

            for one in vectorizer.get_feature_names():
                # print one
                pass

        scaler = StandardScaler(with_mean=False).fit(X_train)
        #X_train = scaler.transform(X_train)

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

        """
        self.clf.append(
            GridSearchCV(MLPClassifier(verbose=False),
                         param_grid={'alpha': [0.01, 0.001, 0.0001],
                                     'hidden_layer_sizes': [
                                         (1000, 500, 100),
                                         (1000, 500), (1000, 1000),
                                         (500, 500), (500, 300), (500, 100) ],
                                     'activation': ['tanh', 'relu'],
                                     'max_iter': [5000, 10000, 15000],
                                     'solver': ['lbfgs']})
        )

        # use_hashing = False
        # {'alpha': 0.0001, 'activation': 'tanh', 'hidden_layer_sizes': (1000, 500)} = score: 0.617486338798
        # {'alpha': 0.001, 'activation': 'relu', 'hidden_layer_sizes': (500, 500)} = 0.612021857923
        # {'alpha': 0.001, 'activation': 'tanh', 'hidden_layer_sizes': (1000, 500), 'max_iter': 5000, 'solver': 'lbfgs'} = 0.73

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

        # self.clf.append(MLPClassifier(alpha=0.001, activation='tanh', max_iter=500, solver='lbfgs', hidden_layer_sizes=(100,)))
        # self.clf.append(MLPClassifier(alpha=0.0001, activation='tanh', max_iter=2000, solver='lbfgs', hidden_layer_sizes=(1000, 500)))
        # self.clf.append(MLPClassifier(alpha=0.001, activation='tanh', max_iter=5000, solver='lbfgs', hidden_layer_sizes=(1000, 500)))
        self.clf.append(MultinomialNB(alpha=0.1))
        self.clf.append(BernoulliNB(binarize=0.0, alpha=0.1))

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
        X_test = self.vectorizer.transform(test)
        #X_test = self.scaler.transform(self.vectorizer.transform(test))

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



if __name__ == '__main__':

    session = CPO.Session()
    import requests

    """
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
        # predictor.dump()
    finally:
        session.close()



