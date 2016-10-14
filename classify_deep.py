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

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s : %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=logging.DEBUG,
                    filename='{}/{}.log'.format(os.path.expanduser("~"), os.path.basename(sys.argv[0])))


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
    logging.debug("Сlassify_deep(). Ошибка чтения настроек CPO.initial_configuration(). {}".format(str(e)))
    raise e


# Проверяем готовность классификатора к работе. Если сервис не создан, создаем по настройкам.
class Predictor():
    desc = "yurburo"
    host = CPO.predictor_hostname
    dd = DD(CPO.predictor_hostname)

    def create(self, client_name='', service_name=''):

        model_repo = "~/models/{}/{}".format(client_name, service_name)

        # dd global variables
        self.dd.set_return_format(self.dd.RETURN_PYTHON)

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

        result = self.dd.put_service(sname, model, description, mllib, parameters_input, parameters_mllib, parameters_output)

        if result['status']['code'] != 201:
            logging.error("Ошибка создания сервиса {}_{}".format(client_name, service_name))
            e = Exception()
            e.message = "Ошибка создания сервиса {}_{}".format(client_name, service_name)
            raise e
        else:
            logging.debug("*** Сервис создан ***")
            logging.debug(result)

    def check(self, sname=''):
        logging.debug("*** Проверка сервиса {} ***".format(sname))

        self.dd.set_return_format(self.dd.RETURN_PYTHON)
        result = self.dd.get_service(sname)
        if result ['status']['code'] != 200:
            logging.debug("*** Сервиса нет ***")
            logging.debug(result)
            return False
        else:
            logging.debug("*** Сервис существует ***")
            logging.debug(result)
            return True

    def classify(self, data=None, sname=None):
        self.dd.set_return_format(self.dd.RETURN_PYTHON)

        parameters_output = {'best': 3}

        classif = self.dd.post_predict(sname, data, {}, {}, parameters_output)
        logging.debug("Service: {}\n Answer: {}\n {} \n".format(sname, classif, "*"*30))

        short_answer = ''
        answer = ''

        return short_answer, answer


predictor = Predictor()

# Получаем реальные данные
session = CPO.Session()

try:
    clear = session.query(CPO.Msg).filter(CPO.Msg.isclassified == 0).limit(args.limit)
except sqlalchemy.orm.exc.NoResultFound as e:
    logging.debug('Новых сообщений нет.')
except Exception as e:
    logging.error("Ошибка при получении очищенных сообщений. {}".format(str(e)))
    raise e
else:
    for row in clear:
        if args.debug:
            logging.debug('*'*100, '\n')
            logging.debug("MSGID: {}, ID: {}".format(row.message_id, row.id))
            logging.debug('От: {}\nКому: {}\nТема: {}'.format(row.sender, row.recipients, row.message_title))
            logging.debug('Текст: \n', row.message_text, '\n')

        # классификация
        try:
            data = ""  # готовим данные из row
            short_answer, answer = predictor.classify(data=data)
        except Exception as e:
            logging.error("Ошибка классфикации для записи. MSGID: {}, ID: {}. \n {}".format(row.message_id,
                                                                                            row.id, str(e)))
        else:
            logging.debug("Категория: ", answer)
            logging.debug('*'*100, '\n')

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
                    logging.error("Ошибка записи в TRAIN_API.", str(e))

    # обновляем статистику после классификации
    if clear and PRODUCTION_MODE:
        logging.debug("Считаем дневную статистику по основным показателям.")
        try:
            CPO.violation_stat_daily()
        except Exception as e:
            logging.error("Ошибка вычисления статистики. ", str(e))
    else:
        logging.debug("*** Система находится в режиме обучения ***")
        logging.debug("*** Статистика не рассчитывается ***")
        logging.debug("clear:", type(clear))
        logging.debug("PRODUCTION_MODE: ", PRODUCTION_MODE)

finally:
    session.close()

