#!/usr/bin/python -t
# coding: utf8

"""

Обновление настроек локального сервиса развернутого на DeepDetect.

"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import objects as CPO
import logging
import os
from dd_client import DD

# Инициализация переменных и констант
try:
    CPO.initial_configuration()
except Exception as e:
    logging.debug("Ошибка чтения настроек CPO.initial_configuration(). {}".format(str(e)))
    raise e


# Проверяем готовность классификатора к работе. Если сервис не создан, создаем по настройкам.
class Predictor():
    desc = CPO.CLIENT_NAME
    host = CPO.PREDICT_SERVICE_HOSTNAME
    port = int(CPO.PREDICT_SERVICE_PORT)
    dd = DD(host=host, port=port)

    def __init__(self):
        self.dd.set_return_format(self.dd.RETURN_PYTHON)

    def create(self, client_name='', service_name=''):

        model_repo = "{}/{}/{}".format(CPO.PREDICT_SERVICE_MODEL_REPO, client_name, service_name)

        # setting up the ML service
        sname = "{}_{}".format(client_name, service_name)
        description = '{} {} service'.format(client_name, service_name)
        mllib = 'caffe'
        sequence = 50

        model = {
            'repository': model_repo
        }

        parameters_input = {
            'connector': 'txt',
            'characters': True,
            'alphabet': u'!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
            'sequence': sequence
        }

        parameters_mllib = {
            'nclasses': 2,
            'finetuning': True,
            'weights': 'model_iter_50000.caffemodel'
        }

        parameters_output = {}

        logging.debug("*** Создаем сервис ***")
        logging.debug("### {} ###".format(sname))

        try:
            result = self.dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, {})
        except Exception as e:
            logging.error("Ошибка обращения к серверу DeepDetect. {}".format(str(e)))
            # Нужно делать уведомления на почту разработчика о таких ошибках
            exit()
        else:
            logging.debug(result)
            if result['status']['code'] != 201:
                logging.error("Ошибка создания сервиса {}_{}".format(client_name, service_name))
                e = Exception()
                e.message = "Ошибка создания сервиса {}_{}".format(client_name, service_name)
                raise e
            else:
                logging.debug("*** Сервис создан ***")

    def check(self, sname=''):
        logging.debug("*** Проверка сервиса {} ***".format(sname))

        try:
            result = self.dd.info()
        except Exception as e:
            logging.error("Ошибка обращения к серверу DeepDetect. {}".format(str(e)))
            # Нужно делать уведомления на почту разработчика о таких ошибках
            exit()
        else:
            logging.debug(result)
            if result['status']['code'] == 200:
                for one in result['head']['services']:
                    if one.get('name') == sname:
                        logging.debug("*** Сервис существует ***")
                        return True

                logging.debug("*** Сервиса нет ***")
                return False

    def classify(self, data=None, sname=None):

        if not isinstance(data, list):
            data = [data]

        self.dd.set_return_format(self.dd.RETURN_PYTHON)

        parameters_output = {'best': 3}
        logging.debug("*** Классификация ***")

        try:
            result = self.dd.post_predict(sname, data, {}, {}, parameters_output)
        except Exception as e:
            logging.error("Ошибка обращения к серверу DeepDetect. {}".format(str(e)))
            # Нужно делать уведомления на почту разработчика о таких ошибках
            raise e
        else:
            logging.debug("Service: {}".format(sname))
            logging.debug("Answer: {}".format(result))
            short = None
            full = ''

            try:
                for one in result['body']['predictions'][0]['classes']:
                    if not short:
                        short = one['cat']
                    if one.get('last'):
                        full += '{}-{}'.format(one['cat'], one['prob'])
                    else:
                        full += '{}-{}:'.format(one['cat'], one['prob'])
            except Exception as e:
                logging.error("Ошибка обработки результата классификации. {}".format(str(e)))
                # Нужно делать уведомления на почту разработчика о таких ошибках
                raise e

            return short, full

    def delete(self, sname=''):
        logging.debug("*** Удалем сервис классификации {} ***".format(sname))

        try:
            result = self.dd.delete_service(sname=sname)
        except Exception as e:
            logging.error("Ошибка обращения к серверу DeepDetect. {}".format(str(e)))
            # Нужно делать уведомления на почту разработчика о таких ошибках
            exit()
        else:
            logging.debug(result)
            logging.debug("*** Удален сервис классификации {} ***".format(sname))

predictor = Predictor()
predictor.delete(sname="{}_{}".format(CPO.CLIENT_NAME, CPO.PREDICT_SERVICE_NAME[0]))

check = predictor.check(sname="{}_{}".format(CPO.CLIENT_NAME, CPO.PREDICT_SERVICE_NAME[0]))

if not check:
    predictor.create(client_name=CPO.CLIENT_NAME, service_name=CPO.PREDICT_SERVICE_NAME[0])

