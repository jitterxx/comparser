# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import time, sys
from dd_client import DD

__author__ = 'sergey'

def mlp_predict(data=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/n20"

    # dd global variables
    sname = 'n20'
    description = 'NN for n20'
    mllib = 'caffe'
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    # layers = [100, 50, 25]
    model = {'repository': model_repo}
    parameters_input = {'connector': 'txt'}
    parameters_mllib = {'nclasses': 2}
    parameters_output = {}

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)


    # classifying
    parameters_input = {}
    parameters_mllib = {}
    parameters_output = {'best': 3}

    classif = dd.post_predict(sname, data, parameters_input, parameters_mllib, parameters_output)
    print classif



    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    #dd.delete_service(sname)

def convnn_predict(data=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/n20_conv"

    # dd global variables
    sname = 'conv20'
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # classifying
    parameters_input = {}
    parameters_mllib = {}
    parameters_output = {'best': 3}

    classif = dd.post_predict(sname, data, parameters_input, parameters_mllib, parameters_output)
    print classif



    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    #dd.delete_service(sname)

def convnn2_predict(data=None):
    host = "localhost"

    # dd global variables
    sname = 'conv20_2'
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # classifying
    parameters_input = {}
    parameters_mllib = {}
    parameters_output = {'best': 3}
    classif = dd.post_predict(sname, data, parameters_input, parameters_mllib, parameters_output)
    print classif


def convnn3_predict(data=None):
    host = "localhost"

    # dd global variables
    sname = 'conv20_2'
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # classifying
    parameters_input = {}
    parameters_mllib = {}
    parameters_output = {'best': 3}

    classif = dd.post_predict(sname, data, parameters_input, parameters_mllib, parameters_output)
    print classif


def uni_predict(data=None, service_name=None):
    # dd global variables
    dd = DD("localhost")
    dd.set_return_format(dd.RETURN_PYTHON)

    # classifying
    parameters_input = {}
    parameters_mllib = {}
    parameters_output = {'best': 3}

    classif = dd.post_predict(service_name, data, parameters_input, parameters_mllib, parameters_output)
    print("Service: {}\n Answer: {}\n {} \n".format(service_name, classif, "*"*30))


if __name__ == '__main__':

    test = ["Спасибо!"]
    """
    test = ["Прошу Вас обратить внимание на следующую ситуацию. Во время моего"
            " отпуска моей коллегой был выкуплен билет Москва-Бухарест-Москва 21-25/09 для нашего сотрудника"
            " Яшиной Екатерины по невозвратному тарифу."
            "Спустя время, начальство попросило меня выкупить билеты для группы сотрудников по "
            "тому же направлению Москва-Бухарест-Москва на те же даты только по возвратному тарифу"
            " (который стоит в два раза дороже). В числе этих сотрудников была и  Екатерина Яшина, "
            "которой был куплен точно такой же билет только по возвратному тарифу."
            "В итоге, у сотрудника - 2 одинаковых билета!"]


    test = ["Яна,доброе утро! Как продвигается наше дело?)"]


    test = ["Екатерина, добрый день, Для подготовки документов нам потребуются: 1\. Действующий Устав; 2\. "
            "Скан или фото паспорта генерального директора (первая страница и страница с пропиской); 3\. Номер и "
            "дата последнего решения или протокола общего собрания участников Общества; 4\. Паспорта участников Общества"
            " (первая страница и страница с пропиской); 5\. Договор аренды, гарантийное письмо и свидетельство о"
            " собственности от БЦ. Если возникнут вопросы, пишите. "]
    """

    service_list = ["conv2_relu", 'conv3_relu', 'conv3_tanh', 'conv4_tanh', 'conv5_tanh', 'sent_ru', 'sent_ru_finetune']

    for one in service_list:
        uni_predict(data=test, service_name=one)

    #mlp_predict(data=test)
    #convnn_predict(data=test)
    #convnn2_predict(data=test)
    #convnn3_predict(data=test)