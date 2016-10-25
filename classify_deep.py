#!/usr/bin/python -t
# coding: utf8

"""

Классификация сообщений.
Используется локальный сервис развернутый на DeepDetect.

"""

import uuid
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import argparse
import mod_classifier_new as clf
import datetime
from configuration import *
import objects as CPO
import sqlalchemy
import logging
import os
from dd_client import DD

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s %(lineno)d : %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=logging.DEBUG,
                    filename='{}/{}{}.log'.format(os.path.expanduser("~"), CPO.LOG_PATH, os.path.basename(sys.argv[0])))


parser = argparse.ArgumentParser(description="Если -с не указано, происходит определение всех "
                                             "категории без проверки. \n"
                                             "Если -l не указано, обрабатываются первые 100 записей.")
parser.add_argument("-l", action="store", help="Количество записей для обработки",dest='limit', type=int)
parser.add_argument("-s", action="store_true", help="Показать классификаторы, категории, лимиты", dest='show')
parser.add_argument("-d", action="store_true", help="Показать отладку.", dest='debug')
args = parser.parse_args()


# Настройка параметров работы
if not args.limit:
    lim = (10,)
else:
    lim = (args.limit,)

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
        logging.debug('classify() - sname = {}'.format(sname))
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

            if result['status']['msg'] == 'OK':
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

                return 'OK', short, full

            else:
                return result['status']['msg'], result, ""


predictor = Predictor()

for service_name in CPO.PREDICT_SERVICE_NAME:
    check = predictor.check(sname="{}_{}".format(CPO.CLIENT_NAME, service_name))

    if not check:
        predictor.create(client_name=CPO.CLIENT_NAME, service_name=service_name)

# Получаем реальные данные
session = CPO.Session()

try:
    clear = session.query(CPO.Msg).filter(CPO.Msg.isclassified == 0).limit(args.limit)
except sqlalchemy.orm.exc.NoResultFound as e:
    logging.debug('*** Новых сообщений нет. ***')
except Exception as e:
    logging.error("Ошибка при получении очищенных сообщений. {}".format(str(e)))
    raise e
else:
    for row in clear:
        logging.debug('{}'.format('*'*100))
        logging.debug("MSGID: {}, ID: {}".format(row.message_id, row.id))
        logging.debug('\nОт: {}\nКому: {}\nТема: {} \nТекст: \n{}\n'.format(row.sender, row.recipients,
                                                                            row.message_title, row.message_text))

        # классификация
        try:
            a1 = list()
            short_answer = None
            status = None
            data = row.message_title + row.message_text  # готовим данные из row
            for service_name in CPO.PREDICT_SERVICE_NAME:
                sname = "{}_{}".format(CPO.CLIENT_NAME, service_name)
                status, a, b = predictor.classify(data=data, sname=sname)
                if status == 'OK':
                    logging.debug("### Service:{}, R_ID:{}, Answer:{}, FullAnswer:{}".format(sname, row.id, a, b))
                    a1.append(b)

                    if service_name == CPO.PREDICT_SERVICE_NAME_DEFAULT:
                        short_answer = a
                else:
                    logging.error("### Service:{}. Ошибка классификации. {}".format(sname, a))

        except Exception as e:
            logging.error("Ошибка классификации для записи. MSGID: {}, ID: {}. \n {}".format(row.message_id,
                                                                                            row.id, str(e)))

        else:
            if not short_answer and not a1:
                # Помечаем запись как ошибочную
                try:
                    row.isclassified = 99
                    row.category = status
                    session.commit()
                except Exception as e:
                    logging.error("Ошибка обновления записи в ClearDB. MSGID: {}, ID: {}".format(row.message_id, row.id))

            else:
                answer = ":".join(a1)
                logging.debug("Категория: {}".format(answer))
                logging.debug('{}'.format('*'*100))

                # Обновляем запись в clearDB
                try:
                    row.isclassified = 1
                    row.category = answer
                    session.commit()
                except Exception as e:
                    logging.error("Ошибка обновления записи в ClearDB. MSGID: {}, ID: {}".format(row.message_id, row.id))
                else:
                    # Добавлем запись в таблицу train_api для работы API и функции переобучения
                    try:
                        new = CPO.TrainAPIRecords()
                        new.uuid = uuid.uuid4().__str__()
                        new.message_id = row.message_id
                        new.auto_cat = short_answer
                        new.category = answer
                        new.date = datetime.datetime.now()
                        new.user_action = 0
                        new.user_answer = ""
                        new.train_epoch = CPO.CURRENT_TRAIN_EPOCH
                        session.add(new)
                        session.commit()
                    except Exception as e:
                        logging.error("Ошибка записи в TRAIN_API. {}".format(str(e)))

    # обновляем статистику после классификации
    if clear and CPO.PRODUCTION_MODE:
        logging.debug("Считаем дневную статистику по основным показателям.")
        try:
            CPO.violation_stat_daily()
        except Exception as e:
            logging.error("Ошибка вычисления статистики. {}".format(str(e)))
    else:
        logging.debug("*** Система находится в режиме обучения ***")
        logging.debug("*** Статистика не рассчитывается ***")
        logging.debug("PRODUCTION_MODE: {}".format(CPO.PRODUCTION_MODE))

finally:
    session.close()

