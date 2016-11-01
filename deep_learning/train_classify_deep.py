# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])


import plotly
from plotly.graph_objs import \
    Scatter, Layout, Data

import time, sys, os, logging
from dd_client import DD
import shutil

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
                            'iterations': 30000,
                            'test_interval': 1000,
                            'base_lr': 0.01,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 3000,
                            'gamma': 0.5,
                            'weight_decay': 0.0004,
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
    f1 = list()
    precis = list()
    iter = list()
    tloss = list()
    rcall = list()

    while True:
        train_status = dd.get_train(sname, job=1, timeout=60)
        if train_status['head']['status'] == 'running':
            mes = train_status['body']['measure']
            logging.debug(mes)
            iter.append(mes.get('iteration'))

            f1.append(mes.get('f1'))
            precis.append(mes.get('precision'))
            tloss.append(mes.get('train_loss'))
            rcall.append(mes.get('recall'))

            f1_data = Scatter(x=iter, y=f1, name="F1")
            precision_data = Scatter(x=iter, y=precis, name='Precision')
            recall_data = Scatter(x=iter, y=rcall, name='Recall')
            loss_data = Scatter(x=iter, y=tloss, name='Train loss')

            data = Data([f1_data, precision_data, recall_data, loss_data])

            plotly.offline.plot(data,  filename=sname+'.html', auto_open=False)
        else:
            logging.debug(train_status)
            break
    logging.debug("### end ###")




def full_trained1(training_repo=None, model_repo=None, sname="custom"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'
    sequence = 500
    layers = ['1CR1024', '1CR256', '1000', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'alphabet': u' {}()[]!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»'
                    u'\абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        # 'finetuning': True,
        # 'weights': 'model_iter_50000.caffemodel'
        'layers': layers,
        'activation': 'relu',  # “sigmoid”,“tanh”,“relu”,“prelu”
        'dropout': 0.4
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
                            'iterations': 2000,
                            'test_interval': 200,
                            'base_lr': 0.0005,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 200,
                            'gamma': 0.5,
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

def full_trained2(training_repo=None, model_repo=None, sname="custom"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'
    sequence = 500
    layers = [2000, 2000, 1000]

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt'
        #'characters': False,
        #'alphabet': u' {}()[]!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»'
        #            u'\абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
        #'sequence': sequence
    }

    parameters_mllib = {
        'template': 'mlp',
        'nclasses': 2,
        # 'finetuning': True,
        # 'weights': 'model_iter_50000.caffemodel'
        'layers': layers,
        'activation': 'prelu',  # “sigmoid”,“tanh”,“relu”,“prelu”
        'dropout': 0.2
        #'class_weights': [0.7449, 0.2551]
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
                        'min_count': 1,
                        'min_word_length': 1,
                        'db': False,
                        'count': False,
                        'tfidf': False
                        #'characters': False
                        #'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 200,
                            'base_lr': 0.005,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 200,
                            'gamma': 0.9,
                            'weight_decay': 0.0001,
                            'solver_type': 'SGD'
                            #'class_weights': [1.0, 0.2551]
                        },
                        'net': {'batch_size': 1}
                        #'class_weights': [1.0, 0.2551]
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    logging.debug("*** Начинаем обучение сети ***")
    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)

    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    f1 = list()
    precis = list()
    iter = list()
    tloss = list()
    rcall = list()

    while True:
        train_status = dd.get_train(sname, job=1, timeout=10)
        if train_status['head']['status'] == 'running':
            mes = train_status['body']['measure']
            logging.debug(mes)
            f1.append(mes.get('f1'))
            iter.append(mes.get('iteration'))
            precis.append(mes.get('precision'))
            tloss.append(mes.get('train_loss'))
            rcall.append(mes.get('recall'))
            f1_data = Scatter(x=iter, y=f1, name="F1")
            precision_data = Scatter(x=iter, y=precis, name='Precision')
            data = Data([f1_data, precision_data])
            plotly.offline.plot(data,  filename=sname+'.html', auto_open=False)
        else:
            logging.debug(train_status)
            break
    logging.debug("### end ###")


def full_trained3(training_repo=None, model_repo=None, sname="custom"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'
    sequence = 500
    layers = ['2CR512', '1000', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'alphabet': u' {}()[]!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»'
                    u'\абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        # 'finetuning': True,
        # 'weights': 'model_iter_50000.caffemodel'
        'layers': layers,
        'activation': 'relu',  # “sigmoid”,“tanh”,“relu”,“prelu”
        'dropout': 0.4
        #'class_weights': [1.0, 0.2551]
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
                        #'class_weights': [1.0, 0.2551]
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 2000,
                            'test_interval': 200,
                            'base_lr': 0.01,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 200,
                            'gamma': 0.1,
                            'weight_decay': 0.0001,
                            'solver_type': 'SGD'
                            #'class_weights': [1.0, 0.2551]
                        },
                        'net': {'batch_size': 10}
                        #'class_weights': [1.0, 0.2551]
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    logging.debug("*** Начинаем обучение сети ***")
    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)

    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    f1 = list()
    precis = list()
    iter = list()
    tloss = list()
    rcall = list()

    while True:
        train_status = dd.get_train(sname, job=1, timeout=10)
        if train_status['head']['status'] == 'running':
            mes = train_status['body']['measure']
            logging.debug(mes)
            f1.append(mes.get('f1'))
            iter.append(mes.get('iteration'))
            precis.append(mes.get('precision'))
            tloss.append(mes.get('train_loss'))
            rcall.append(mes.get('recall'))
            f1_data = Scatter(x=iter, y=f1, name="F1")
            precision_data = Scatter(x=iter, y=precis, name='Precision')
            data = Data([f1_data, precision_data])
            plotly.offline.plot(data,  filename=sname+'.html', auto_open=False)
        else:
            logging.debug(train_status)
            break
    logging.debug("### end ###")


def full_trained4(training_repo=None, model_repo=None, sname="custom"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'
    sequence = 100
    layers = ['1CR500', '1CR500', '1CR500', '1000', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'alphabet': u' {}()[]!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»'
                    u'\абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        # 'finetuning': True,
        # 'weights': 'model_iter_50000.caffemodel'
        'layers': layers,
        'activation': 'relu',  # “sigmoid”,“tanh”,“relu”,“prelu”
        'dropout': 0.5
        #'class_weights': [1.0, 0.2551]
    }

    parameters_output = {}

    logging.debug("*** Создаем сервис ***")
    logging.debug("### {} ###".format(sname))

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    logging.debug("*** Готово! ***")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.05,
                        #'min_count': 2,
                        #'min_word_length': 2,
                        'db': False,
                        #'count': False,
                        #'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        #'class_weights': [1.0, 0.2551]
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 2000,
                            'test_interval': 200,
                            'base_lr': 0.01,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 200,
                            'gamma': 0.5,
                            #'weight_decay': 0.0001,
                            'solver_type': 'SGD'
                            #'class_weights': [1.0, 0.2551]
                        },
                        'net': {'batch_size': 10}
                        #'class_weights': [1.0, 0.2551]
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    logging.debug("*** Начинаем обучение сети ***")
    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)

    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    f1 = list()
    precis = list()
    iter = list()
    tloss = list()
    rcall = list()

    while True:
        train_status = dd.get_train(sname, job=1, timeout=10)
        if train_status['head']['status'] == 'running':
            mes = train_status['body']['measure']
            logging.debug(mes)
            f1.append(mes.get('f1'))
            iter.append(mes.get('iteration'))
            precis.append(mes.get('precision'))
            tloss.append(mes.get('train_loss'))
            rcall.append(mes.get('recall'))
            f1_data = Scatter(x=iter, y=f1, name="F1")
            precision_data = Scatter(x=iter, y=precis, name='Precision')
            data = Data([f1_data, precision_data])
            plotly.offline.plot(data,  filename=sname+'.html', auto_open=False)
        else:
            logging.debug(train_status)
            break
    logging.debug("### end ###")


def full_trained5(training_repo=None, model_repo=None, mname="custom"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'

    sequence = [100, 100, 200, 200]

    layers = [
        ['1CR256', '1CR256', '1000', '1000'],
        ['1CR512', '1CR512', '1000', '1000'],
        ['1CR256', '1CR256', '1000', '1000'],
        ['1CR512', '1CR512', '1000', '1000']
    ]

    for i in range(len(sequence)):
        try:
            sname = '{}_num_{}'.format(mname, i)
            rep_dir = model_repo + sname
            if os.path.exists(rep_dir):
                print("Удаляем каталог и старые данные...")
                shutil.rmtree(rep_dir)

            print("Создаем новый каталог: {}".format(rep_dir))
            os.makedirs(rep_dir)

            model = {
                'templates': '/home/sergey/deepdetect/templates/caffe',
                'repository': rep_dir
            }

            parameters_input = {
                'connector': 'txt',
                'characters': True,
                'alphabet': u'{}()[]!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
                'sequence': sequence[i]
            }

            parameters_mllib = {
                'template': 'convnet',
                'nclasses': 2,
                # 'finetuning': True,
                # 'weights': 'model_iter_50000.caffemodel'
                'layers': layers[i],
                'activation': 'prelu',  # “sigmoid”,“tanh”,“relu”,“prelu”
                'dropout': 0.2
                #'class_weights': [1.0, 0.2551]
            }

            parameters_output = {}

            logging.debug("*** Создаем сервис ***")
            logging.debug("### {} ###".format(sname))

            dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
            logging.debug("*** Готово! ***")

            # training
            train_data = [training_repo]
            parameters_input = {'shuffle': True,
                                'test_split': 0.05,
                                #'min_count': 2,
                                #'min_word_length': 2,
                                'db': False,
                                #'count': False,
                                #'tfidf': False,
                                'sentences': True,
                                'characters': True,
                                'sequence': sequence[i]
                                #'class_weights': [1.0, 0.2551]
                                }

            parameters_mllib = {'gpu': False,
                                'solver': {
                                    'iterations': 2000,
                                    'test_interval': 100,
                                    'base_lr': 0.005,
                                    'momentum': 0.9,
                                    'lr_policy': 'step',
                                    'stepsize': 100,
                                    'gamma': 0.9,
                                    'weight_decay': 0.0004,
                                    'solver_type': 'SGD'
                                    #'class_weights': [1.0, 0.2551]
                                },
                                'net': {'batch_size': 10}
                                #'class_weights': [1.0, 0.2551]
                                }

            parameters_output = {'measure': ['mcll', 'f1', 'auc']}

            logging.debug("*** Начинаем обучение сети ***")
            dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)

            # report on results every 10 seconds
            time.sleep(1)
            train_status = ''
            f1 = list()
            precis = list()
            iter = list()
            tloss = list()
            rcall = list()

            while True:
                train_status = dd.get_train(sname, job=1, timeout=60)
                if train_status['head']['status'] == 'running':
                    mes = train_status['body']['measure']
                    logging.debug(mes)
                    f1.append(mes.get('f1'))
                    iter.append(mes.get('iteration'))
                    precis.append(mes.get('precision'))
                    tloss.append(mes.get('train_loss'))
                    rcall.append(mes.get('recall'))

                    f1_data = Scatter(x=iter, y=f1, name="F1")
                    precision_data = Scatter(x=iter, y=precis, name='Precision')
                    recall_data = Scatter(x=iter, y=rcall, name='Recall')
                    loss_data = Scatter(x=iter, y=tloss, name='Train loss')

                    data = Data([f1_data, precision_data, recall_data, loss_data])

                    plotly.offline.plot(data,  filename=sname+'.html', auto_open=False)
                else:
                    logging.debug(train_status)
                    break
            logging.debug("### end ###")
        except Exception as e:
            print "Ошибка: {}".format(str(e))


def full_trained6(training_repo=None, model_repo=None, mname="custom"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'

    sequence = [200]

    layers = [['1CR256', '1CR256', '1CR256', '1000', '1000']]

    for i in range(len(sequence)):
        try:
            sname = '{}_num_{}'.format(mname, i)
            rep_dir = model_repo + sname
            if os.path.exists(rep_dir):
                print("Удаляем каталог и старые данные...")
                shutil.rmtree(rep_dir)

            print("Создаем новый каталог: {}".format(rep_dir))
            os.makedirs(rep_dir)

            model = {
                'templates': '/home/sergey/deepdetect/templates/caffe',
                'repository': rep_dir
            }

            parameters_input = {
                'connector': 'txt',
                'characters': True,
                'alphabet': u'-0123456789?_abcdefghijklmnopqrstuvwxyzабвгдежзийклмнопрстуфхцчшщъыьэюяё',
                'sequence': sequence[i]
            }

            parameters_mllib = {
                'template': 'convnet',
                'nclasses': 2,
                # 'finetuning': True,
                # 'weights': 'model_iter_50000.caffemodel'
                'layers': layers[i],
                'activation': 'relu',  # “sigmoid”,“tanh”,“relu”,“prelu”
                'dropout': 0.5
                #'class_weights': [1.0, 0.2551]
            }

            parameters_output = {}

            logging.debug("*** Создаем сервис ***")
            logging.debug("### {} ###".format(sname))

            dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
            logging.debug("*** Готово! ***")

            # training
            train_data = [training_repo]
            parameters_input = {'shuffle': True,
                                'test_split': 0.05,
                                #'min_count': 2,
                                #'min_word_length': 2,
                                'db': False,
                                #'count': False,
                                #'tfidf': False,
                                'sentences': False,
                                'characters': True,
                                'sequence': sequence[i]
                                #'class_weights': [1.0, 0.2551]
                                }

            parameters_mllib = {'gpu': False,
                                'solver': {
                                    'iterations': 2000,
                                    'test_interval': 100,
                                    'base_lr': 0.01,
                                    #'momentum': 0.9,
                                    #'lr_policy': 'step',
                                    #'stepsize': 500,
                                    'gamma': 0.5,
                                    #'weight_decay': 0.0004,
                                    'solver_type': 'SGD'
                                    #'class_weights': [1.0, 0.2551]
                                },
                                'net': {'batch_size': 1, 'test_batch_size': 1}
                                #'class_weights': [1.0, 0.2551]
                                }

            parameters_output = {'measure': ['mcll', 'f1', 'auc']}

            logging.debug("*** Начинаем обучение сети ***")
            dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)

            # report on results every 10 seconds
            time.sleep(1)
            train_status = ''
            f1 = list()
            precis = list()
            iter = list()
            tloss = list()
            rcall = list()

            while True:
                train_status = dd.get_train(sname, job=1, timeout=60)
                if train_status['head']['status'] == 'running':
                    mes = train_status['body']['measure']
                    logging.debug(mes)
                    f1.append(mes.get('f1'))
                    iter.append(mes.get('iteration'))
                    precis.append(mes.get('precision'))
                    tloss.append(mes.get('train_loss'))
                    rcall.append(mes.get('recall'))

                    f1_data = Scatter(x=iter, y=f1, name="F1")
                    precision_data = Scatter(x=iter, y=precis, name='Precision')
                    recall_data = Scatter(x=iter, y=rcall, name='Recall')
                    loss_data = Scatter(x=iter, y=tloss, name='Train loss')

                    data = Data([f1_data, precision_data, recall_data, loss_data])

                    plotly.offline.plot(data,  filename=sname+'.html', auto_open=False)
                else:
                    logging.debug(train_status)
                    break
            logging.debug("### end ###")
        except Exception as e:
            print "Ошибка: {}".format(str(e))


def full_trained12(training_repo=None, model_repo=None, sname="custom"):
    host = "localhost"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    description = 'classification'
    mllib = 'caffe'
    sequence = 500
    layers = ['1CR2000', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt'
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        'layers': layers,
        'activation': 'relu',
        'dropout': 0.2
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
                        'min_count': 2,
                        'min_word_length': 2
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 2000,
                            'test_interval': 100,
                            'base_lr': 0.01,
                            'gamma': 0.5
                        },
                        'net': {'batch_size': 1}
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    logging.debug("*** Начинаем обучение сети ***")
    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)


    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    f1 = list()
    precis = list()
    iter = list()
    tloss = list()
    rcall = list()

    while True:
        train_status = dd.get_train(sname, job=1, timeout=10)
        if train_status['head']['status'] == 'running':
            mes = train_status['body']['measure']
            logging.debug(mes)
            f1.append(mes.get('f1'))
            iter.append(mes.get('iteration'))
            precis.append(mes.get('precision'))
            tloss.append(mes.get('train_loss'))
            rcall.append(mes.get('recall'))

            f1_data = Scatter(x=iter, y=f1, name="F1")
            precision_data = Scatter(x=iter, y=precis, name='Precision')
            recall_data = Scatter(x=iter, y=rcall, name='Recall')
            loss_data = Scatter(x=iter, y=tloss, name='Train loss')

            data = Data([f1_data, precision_data, recall_data, loss_data])

            plotly.offline.plot(data,  filename=sname+'.html', auto_open=False)
        else:
            logging.debug(train_status)
            break
    logging.debug("### end ###")



if __name__ == '__main__':
    #finetune(training_repo="/home/sergey/deep/yurburo/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo/models/yurburo/default")

    #finetune(training_repo="/home/sergey/deep/yurburo2/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo2/models/yurburo/unbalanced_110",
    #         sname="unbalanced_110")

    #finetune(training_repo="/home/sergey/deep/yurburo3/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo3/models/yurburo/reversed_category",
    #         sname="reverse_category")

    #finetune(training_repo="/home/sergey/deep/yurburo4/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo4/models/yurburo/unbalanced_210",
    #         sname="unbalanced_210")

    #full_trained1(training_repo="/home/sergey/deep/yurburo5/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo5/models/yurburo/full_trained",
    #         sname="full_trained1")

    #full_trained2(training_repo="/home/sergey/deep/yurburo6/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo6/models/yurburo/full_trained",
    #         sname="full_trained2")

    #full_trained3(training_repo="/home/sergey/deep/yurburo7/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo7/models/yurburo/full_trained",
    #         sname="full_trained3")

    #full_trained4(training_repo="/home/sergey/deep/yurburo8/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo8/models/yurburo/full_trained",
    #         sname="full_trained4")

    #full_trained5(training_repo="/home/sergey/deep/yurburo9/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo9/models/",
    #         mname="full_trained6")

    #finetune(training_repo="/home/sergey/deep/yurburo10/yurburo_train_data",
    #         model_repo="/home/sergey/deep/yurburo10/models/yurburo/unbalanced_210_new",
    #         sname="unbalanced_210_new")

    full_trained6(training_repo="/home/sergey/deep/yurburo11/200_train_data",
             model_repo="/home/sergey/deep/yurburo11/models/",
             mname="full_trained11")

    #full_trained12(training_repo="/home/sergey/deep/yurburo12/news20",
    #         model_repo="/home/sergey/deep/yurburo12/models",
    #         sname="full_trained12")
