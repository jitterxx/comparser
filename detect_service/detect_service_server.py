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
from deep_learning.mod_classifier_test import mytoken, specfeatures_new2, features_extractor2

__author__ = 'sergey'


SERVICES = dict()
service_root_dir = '/home/sergey/dev/conflict analyser/detect_service'


class Predict(object):

    exposed = True

    def POST(self, service=None, data=None, **kwargs):

        print service
        print data
        print cherrypy.request.body_params

        if not service:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Service name MUST be in request.'})

        if not data:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Data MUST be send in request.'})

        if not SERVICES.get(service) and not SERVICES.get(service):
            print("Predict(). Service: {}. Service NOT created.".format(service))
            cherrypy.response.status = 404
            cherrypy.response.body = 'error'
            return json.dumps({'status': 404, 'message': "Service NOT created."})

        try:
            X_test = SERVICES.get(service)[0].transform(data)
            result = SERVICES.get(service)[1].predict(X_test)
        except Exception as e:
            print("Predict(). Service: {}. Error. {}".format(service, str(e)))
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': str(e)})
        else:
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': '{}'.format(result)})


class Create(object):

    exposed = True

    def POST(self, service=None):

        if not service:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Service name MUST be in request.'})

        # ищем и загружаем сохраненный сервис
        service_dir = service_root_dir + '/' + service + '/'
        try:
            vectorizer = joblib.load('{}{}_vectorizer.pkl'.format(service_dir, service))
            clf = joblib.load('{}{}_clf.pkl'.format(service_dir, service))
        except Exception as e:
            print("Create(). Service: {}. Ошибка. {}".format(service, str(e)))
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': str(e)})
        else:
            SERVICES[service] = [vectorizer, clf]
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': 'Service {} created'.format(service)})


class Info(object):

    exposed = True

    def GET(self, service=None):

        if not service:
            resp = list()
            for one in SERVICES.keys():
                resp.append({'name': one, 'status': 'ok'})

            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': 'Service list.', 'services': resp})

        # ищем и загружаем сохраненный сервис
        if not SERVICES.get(service) and not SERVICES.get(service):
            print("Predict(). Service: {}. Service NOT created.".format(service))
            cherrypy.response.status = 404
            cherrypy.response.body = 'error'
            return json.dumps({'status': 404, 'message': "Service NOT created."})
        else:
            print("Predict(). Service: {}. Service created.".format(service))
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': "Service {} created.".format(service)})



class Root(object):

    @cherrypy.expose
    def index(self):
       return None

    @cherrypy.expose
    def info(self, service_name=None):
       return None


root = Root()
root.predict = Predict()
root.create = Create()
root.info = Info()

conf = {
    'global': {
        'server.socket_host': '127.0.0.1',
        'server.socket_port': 9990,
    },
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
    }
}

if __name__ == '__main__':

    CPO.initial_configuration()
    cherrypy.quickstart(root, '/', conf)


