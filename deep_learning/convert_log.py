# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])


import objects as CPO
import cherrypy
import re
import os
import uuid
import shutil
import json


__author__ = 'sergey'


session = CPO.Session()
PATH = "./conparser_data"

cats = CPO.GetCategory().keys()

graph_data = dict()

f = file('nn.log', "r")
while True:
    line = f.readline()
    if line == '### end ###':
        # конец данных сети
        raw_input("Конец данных... Дальше?")
        pass
    elif re.search('### \s+ ###', line):
        # начало данных новой сети
        service_name = line.split(" ")[1]
        graph_data[service_name] = {"f1": list(), "precision": list(), "accuracy": list()}
    elif re.search('\*\*\* \s+ \*\*\*', line):
        # коммент пропускаем
        pass
    else:
        data = json.loads(line)
        if data.get('status'):
            # обучение закончилось, конечный результат
            pass
        else:
            graph_data[service_name]['f1'].append(data.get('f1'))
            graph_data[service_name]['precision'].append(data.get('precision'))
            graph_data[service_name]['accuracy'].append(data.get('accp'))


f.close()