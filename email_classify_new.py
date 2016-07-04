#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""
import argparse
import mod_classifier_new as clf
import datetime
from configuration import *
import objects as CPO
import sqlalchemy

import uuid
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


parser = argparse.ArgumentParser(description="Если -с не указано, происходит определение всех "
                                             "категории без проверки. \n"
                                             "Если -l не указано, обрабатываются первые 100 записей.")
parser.add_argument("-l",action="store",help="Количество записей для обработки",dest='limit',type=int)
parser.add_argument("-s",action="store_true",help="Показать классификаторы, категории, лимиты",dest='show')
parser.add_argument("-d",action="store_true",help="Показать отладку.",dest='debug')
args = parser.parse_args()

# Настройка параметров работы
if not args.limit:
    lim = (10,)
else:
    lim = (args.limit,)

# Инициализация переменных и констант
CPO.initial_configuration()


# Получаем реальные данные
session = CPO.Session()

try:
    clear = session.query(CPO.Msg).filter(CPO.Msg.isclassified == 0).limit(args.limit)
except sqlalchemy.orm.exc.NoResultFound as e:
    if args.debug:
        print 'Новых сообщений нет.'
except Exception as e:
    if args.debug:
        print "email_classify_new. Ошибка при получении очищенных сообщений. %s" % str(e)
    raise e
else:
    # Создаем классификатор и инициализируем его
    if args.debug:
        print "Создаем классификатор и инициализируем его"

    predictor = clf.ClassifierNew()
    # predictor.init_and_fit(debug=args.debug)
    predictor.init_and_fit_new(debug=args.debug)

    for row in clear:
        if args.debug:
            print '*'*100,'\n'
            print "MSGID: %s, ID: %s" % (row.message_id, row.id)
            print('От: {}\nКому: {}\nТема: {}'.format(row.sender, row.recipients, row.message_title))
            print 'Текст: \n', row.message_text, '\n'

        # классификация
        try:
            # answer = predictor.classify(data=row)
            short_answer, answer = predictor.classify_new(data=row, debug=args.debug)
        except Exception as e:
            if args.debug:
                print "email_classify_new(). Ошибка классфикации для записи. MSGID: %s, ID: %s" % \
                      (row.message_id, row.id)
                print str(e)
        else:
            if args.debug:
                print "Категория: %s" % answer
                print '*'*100,'\n'

            # Обновляем запись в clearDB
            try:
                row.isclassified = 1
                row.category = answer
                session.commit()
            except Exception as e:
                if args.debug:
                    print "ERROR. Ошибка обновления записи в ClearDB. MSGID: %s, ID: %s" % (row.message_id, row.id)
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
                    if args.debug:
                        print "email_classify_new(). Ошибка записи в TRAIN_API. %s" % str(e)

                # Добавлем задачу, если категория в WARNING_CAT
                # Добавление происходит после проверки пользователем
                """
                try:
                    if short_answer in WARNING_CATEGORY:
                        # вычисляем ответственного за закрытие задачи
                        # Стандартно это ответственный за клиента или менеджера
                        responsible = CPO.get_message_responsible(msg_id=row.message_id)
                        if not responsible:
                            responsible = "UNKNOWN-UUID"
                        task_uuid = CPO.create_task(responsible=responsible, message_id=row.message_id)
                        comment = "Задача создана автоматически."
                        CPO.add_task_comment(task_uuid=task_uuid, comment=comment)
                except Exception as e:
                    if args.debug:
                        print "email_classify_new(). Ошибка создания Задачи. %s" % str(e)
                """

finally:
    session.close()

