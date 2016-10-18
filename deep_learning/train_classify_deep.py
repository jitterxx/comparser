# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])



import time, sys, os, logging
from dd_client import DD

__author__ = 'sergey'

logging.basicConfig(format='%(message)s',
                    level=logging.DEBUG,
                    filename='train_classify_deep.log')


def finetune(training_repo=None, model_repo=None, sname="Finetune"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'
    sequence = 50
    # layers = ['1CR256', '1CR256', '1000', '1000']

    model = {
        # 'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'alphabet': u'!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
        'sequence': sequence
    }

    parameters_mllib = {
        #'template': 'convnet',
        'nclasses': 2,
        'finetuning': True,
        'weights': 'model_iter_50000.caffemodel'
        #'layers': layers,
        #'activation': 'tanh',  # “sigmoid”,“tanh”,“relu”,“prelu”
        #'dropout': 0.5
    }

    parameters_output = {}

    logging.debug("*** Создаем сервис ***")
    logging.debug("### {} ###".format(sname))

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    logging.debug("*** Готово! ***")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.1,
                        #'min_count': 2,
                        #'min_word_length': 2,
                        'db': False,
                        #'count': False,
                        #'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 1000,
                            'test_interval': 50,
                            'base_lr': 0.0005,
                            'momentum': 0.9,
                            #'lr_policy': 'step',
                            #'stepsize': 100,
                            #'gamma': 0.5,
                            'weight_decay': 0.0001,
                            'solver_type': 'SGD'
                        },
                        'net': {'batch_size': 10}
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    logging.debug("*** Начинаем обучение сети ***")
    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)

    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    while True:
        train_status = dd.get_train(sname, job=1, timeout=10)
        if train_status['head']['status'] == 'running':
            logging.debug(train_status['body']['measure'])
        else:
            logging.debug(train_status)
            break
    logging.debug("### end ###")



if __name__ == '__main__':
    #finetune(training_repo="/home/sergey/deep/yurburo/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo/models/yurburo/default")

    finetune(training_repo="/home/sergey/deep/yurburo2/yurburo_train_data",
             model_repo="/home/sergey/deep/yurburo2/models/yurburo/unbalanced_110",
             sname="unbalanced_110")

    finetune(training_repo="/home/sergey/deep/yurburo3/yurburo_train_data",
             model_repo="/home/sergey/deep/yurburo3/models/yurburo/reversed_category",
             sname="reverse_category")

