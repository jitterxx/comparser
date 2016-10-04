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
                    filename='nn.log')

# training_data = "/home/sergey/deep/models/n20/news20"


def mlp_net(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/n20"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'n20'
    description = 'NN for n20'
    mllib = 'caffe'
    # layers = [100, 50, 25]
    layers = [1500, 1000, 500]

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {'connector': 'txt'}

    parameters_mllib = {
        'template': 'mlp',
        'nclasses': 2,
        'layers': layers,
        'activation': 'relu',
        'dropout': 0.2
    }

    parameters_output = {}

    print("Создаем сервис...")

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    print("Готово!")

    print("Начинаем обучение сети...")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False}

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 20000,
                            'test_interval': 1000,
                            'base_lr': 0.001,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 500,
                            'gamma': 0.5,
                            'solver_type': 'SGD'
                        },
                        'net': {'batch_size': 1}
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)


    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    while True:
        train_status = dd.get_train(sname,job=1,timeout=10)
        if train_status['head']['status'] == 'running':
            print train_status['body']['measure']
        else:
            print train_status
            break

    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    dd.delete_service(sname)


def conv_net(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/n20_conv"

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'conv20'
    description = 'ConvNN for n20'
    mllib = 'caffe'
    sequence = 150
    # layers = [100, 50, 25]
    # layers = [1000, 1000]
    layers = ['1CR256', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        'layers': layers,
        'activation': 'relu',
        'dropout': 0.5
    }

    parameters_output = {}

    print("Создаем сервис...")

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    print("Готово!")

    print("Начинаем обучение сети...")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 100,
                            'base_lr': 0.01,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 500,
                            'gamma': 0.5,
                            'weight_decay': 0.00001,
                            'solver_type': 'SGD'
                        },
                        'net': {'batch_size': 1}
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)


    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    while True:
        train_status = dd.get_train(sname,job=1,timeout=10)
        if train_status['head']['status'] == 'running':
            print train_status['body']['measure']
        else:
            print train_status
            break

    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)


def conv_net2(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/n20_conv2"

    if not os.path.exists(model_repo):
        os.mkdir(model_repo)


    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'conv2_relu'
    description = 'ConvNN 1 layer relu'
    mllib = 'caffe'
    sequence = 500
    # layers = [100, 50, 25]
    # layers = [1000, 1000]
    layers = ['1CR256', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        'layers': layers,
        'activation': 'relu',
        'dropout': 0.5
    }

    parameters_output = {}

    logging.debug("*** Создаем сервис ***")
    logging.debug("### {} ###".format(sname))

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    logging.debug("*** Готово! ***")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 500,
                            'base_lr': 0.01,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 1000,
                            'gamma': 0.5,
                            'weight_decay': 0.00001,
                            'solver_type': 'SGD'
                        },
                        'net': {'batch_size': 1}
                        }

    parameters_output = {'measure': ['mcll', 'f1']}

    logging.debug("*** Начинаем обучение ***")
    dd.post_train(sname, train_data, parameters_input, parameters_mllib, parameters_output, async=True)


    # report on results every 10 seconds
    time.sleep(1)
    train_status = ''
    while True:
        train_status = dd.get_train(sname,job=1,timeout=10)
        if train_status['head']['status'] == 'running':
            logging.debug(train_status['body']['measure'])
        else:
            logging.debug(train_status)
            break

    logging.debug("### end ###")

    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)


def conv_net3(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/conv3"

    if not os.path.exists(model_repo):
        os.mkdir(model_repo)


    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'conv3_relu'
    description = 'ConvNN 2 layer relu'
    mllib = 'caffe'
    sequence = 500
    # layers = [100, 50, 25]
    # layers = [1000, 1000]
    layers = ['2CR256', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        'layers': layers,
        'activation': 'relu',
        'dropout': 0.5
    }

    parameters_output = {}

    logging.debug("*** Создаем сервис ***")
    logging.debug("### {} ###".format(sname))

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    logging.debug("*** Готово! ***")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 500,
                            'base_lr': 0.001,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 500,
                            'gamma': 0.5,
                            'weight_decay': 0.00001,
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
        train_status = dd.get_train(sname,job=1,timeout=10)
        if train_status['head']['status'] == 'running':
            logging.debug(train_status['body']['measure'])
        else:
            logging.debug(train_status)
            break

    logging.debug("### end ###")

    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)


def conv_net3_tanh(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/conv3_tanh"

    if not os.path.exists(model_repo):
        os.mkdir(model_repo)

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'conv3_tanh'
    description = 'ConvNN 1 layer tanh '
    mllib = 'caffe'
    sequence = 100
    # layers = [100, 50, 25]
    # layers = [1000, 1000]
    layers = ['1CR256', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        'layers': layers,
        'activation': 'tanh',  # “sigmoid”,“tanh”,“relu”,“prelu”
        'dropout': 0.5
    }

    parameters_output = {}

    logging.debug("*** Создаем сервис ***")
    logging.debug("### {} ###".format(sname))

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    logging.debug("*** Готово! ***")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 500,
                            'base_lr': 0.001,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 500,
                            'gamma': 0.5,
                            'weight_decay': 0.00001,
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


    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)

def conv_net4_tanh(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/conv4_tanh"

    if not os.path.exists(model_repo):
        os.mkdir(model_repo)

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'conv4_tanh'
    description = 'ConvNN tanh 2 layers'
    mllib = 'caffe'
    sequence = 500
    layers = ['1CR256', '1CR256', '1000', '1000']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        'layers': layers,
        'activation': 'tanh',  # “sigmoid”,“tanh”,“relu”,“prelu”
        'dropout': 0.5
    }

    parameters_output = {}

    logging.debug("*** Создаем сервис ***")
    logging.debug("### {} ###".format(sname))

    dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)
    logging.debug("*** Готово! ***")

    # training
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 500,
                            'base_lr': 0.001,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 500,
                            'gamma': 0.5,
                            'weight_decay': 0.00001,
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

    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)

def conv_net5_tanh(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/conv5_tanh"

    if not os.path.exists(model_repo):
        os.mkdir(model_repo)

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'conv5_tanh'
    description = 'ConvNN tanh 3 layers'
    mllib = 'caffe'
    sequence = 500
    layers = ['1CR32', '1CR64', '1CR128', '1024']

    model = {
        'templates': '/home/sergey/deepdetect/templates/caffe',
        'repository': model_repo
    }

    parameters_input = {
        'connector': 'txt',
        'characters': True,
        'sequence': sequence
    }

    parameters_mllib = {
        'template': 'convnet',
        'nclasses': 2,
        'layers': layers,
        'activation': 'prelu',  # “sigmoid”,“tanh”,“relu”,“prelu”
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
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 500,
                            'base_lr': 0.001,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 500,
                            'gamma': 0.5,
                            'weight_decay': 0.00001,
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

    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)


def sent_ru(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/sent_ru_char"

    if not os.path.exists(model_repo):
        os.mkdir(model_repo)

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'sent_ru'
    description = 'Russian sentiment classification'
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
        'nclasses': 2
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
    """
    train_data = [training_repo]
    parameters_input = {'shuffle': True,
                        'test_split': 0.2,
                        'min_count': 2,
                        'min_word_length': 2,
                        'db': False,
                        'count': False,
                        'tfidf': False,
                        'characters': True,
                        'sequence': sequence
                        }

    parameters_mllib = {'gpu': False,
                        'solver': {
                            'iterations': 5000,
                            'test_interval': 500,
                            'base_lr': 0.001,
                            'momentum': 0.9,
                            'lr_policy': 'step',
                            'stepsize': 500,
                            'gamma': 0.5,
                            'weight_decay': 0.00001,
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
    """
    logging.debug("### end ###")
    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)


def sent_ru_finetune(training_repo=None):
    host = "localhost"
    model_repo = "/home/sergey/deep/models/sent_ru_char_finetune"

    if not os.path.exists(model_repo):
        os.mkdir(model_repo)

    # dd global variables
    dd = DD(host)
    dd.set_return_format(dd.RETURN_PYTHON)

    # setting up the ML service
    sname = 'sent_ru_finetune'
    description = 'Russian sentiment classification'
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
    # deleting the service, keeping the model (use clear='lib' to clear the model as well)
    # dd.delete_service(sname)


if __name__ == '__main__':
    #mlp_net(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    #conv_net(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    #conv_net2(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    #conv_net3(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    #conv_net3_tanh(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    #conv_net4_tanh(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    #conv_net5_tanh(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    #sent_ru(training_repo="/home/sergey/deep/models/train_data/conparser_data")
    sent_ru_finetune(training_repo="/home/sergey/deep/models/train_data/conparser_data")

    pass