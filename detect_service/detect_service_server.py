# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import re
import os
import json
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

import cherrypy
from bs4 import BeautifulSoup
from mako.lookup import TemplateLookup
import datetime
import pickle
from sklearn.externals import joblib

__author__ = 'sergey'


class Root(object):

    services = dict()
    service_root_dir = '/home/sergey/dev/conflict analyser/detect_service'


    @cherrypy.expose
    def index(self):
       return None

    @cherrypy.expose
    def create(self, service_name=None):

        if not service_name:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Service name MUST be in request.'})

        # ищем и загружаем сохраненный сервис
        service_dir = self. service_root_dir + '/' + service_name + '/'
        try:
            vectorizer = joblib.load('{}{}_vectorizer.pkl'.format(service_dir, service_name))
            clf = joblib.load('{}{}_clf.pkl'.format(service_dir, service_name))
        except Exception as e:
            print("Create(). Service: {}. Ошибка. {}".format(service_name, str(e)))
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': str(e)})
        else:
            self.services[service_name] = [vectorizer, clf]
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': 'Service {} created'.format(service_name)})

    @cherrypy.expose
    def predict(self, service=None, data=None):

        print service
        print data

        if not service:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Service name MUST be in request.'})

        if not data:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Data MUST be send in request.'})

        try:
            X_test = self.services.get(service)[0].transform(data)
            result = self.services.get(service)[1].predict(X_test)
        except Exception as e:
            print("Predict(). Service: {}. Ошибка. {}".format(service, str(e)))
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': str(e)})
        else:
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': '{}'.format(result)})

    @cherrypy.expose
    def info(self, service_name=None):
       return None

cherrypy.config.update("detect_service_server.config")

if __name__ == '__main__':
    CPO.initial_configuration()
    cherrypy.quickstart(Root(), '/', "detect_service_app.config")
