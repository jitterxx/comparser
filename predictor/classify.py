#!/usr/bin/python3 -t
# coding: utf8


import argparse
import tf_cnn as clf
import datetime
import sqlalchemy
import os
import uuid
import sys
sys.path.extend(['..'])

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


parser = argparse.ArgumentParser(description="Если -l не указано, обрабатываются первые 10 записей.")
parser.add_argument("-l",action="store",help="Количество записей для обработки",dest='limit',type=int)
parser.add_argument("-d",action="store_true",help="Показать отладку.",dest='debug')
args = parser.parse_args()

# Настройка параметров работы
if not args.limit:
    lim = (10,)
else:
    lim = (args.limit,)


# Получаем реальные данные

import shutil

Base = automap_base()

# engine, suppose it has two tables 'user' and 'address' set up
sql_uri = "mysql://%s:%s@%s:%s/%s?charset=utf8" % ('conparser', 'Qazcde123', '127.0.0.1', '3306', 'yurburo')
engine = create_engine(sql_uri)

# reflect the tables
Base.prepare(engine, reflect=True)

# mapped classes are now created with names by default
# matching that of the table name.
Msg = Base.classes.email_cleared_data
TrainAPIRecords = Base.classes.train_api
Settings = Base.classes.settings

session = Session(engine)

CURRENT_TRAIN_EPOCH = 0

try:
    resp = session.query(Settings).one_or_none()
except Exception as e:
    session.close()
    raise e
else:
    if resp:
        CURRENT_TRAIN_EPOCH = resp.train_epoch
    else:
        print('************** Не найдена текущая эпоха в базе. *****************')
        session.close()
        sys.exit()

try:
    clear = session.query(Msg).filter(Msg.isclassified == 0).limit(args.limit)
except sqlalchemy.orm.exc.NoResultFound as e:
    if args.debug:
        print('Новых сообщений нет.')
except Exception as e:
    if args.debug:
        print("predictor.classify(). Ошибка при получении очищенных сообщений. {}".format(str(e)))
    raise e
else:
    # Создаем классификатор и инициализируем его
    predictor = clf.ClassifierNew()
    # predictor.init_and_fit(debug=args.debug)
    predictor.init_and_fit()

    for row in clear:
        if args.debug:
            print('*'*100,'\n')
            print("MSGID: {}, ID: {}".format(row.message_id, row.id))
            print('От: {}\nКому: {}\nТема: {}'.format(row.sender, row.recipients, row.message_title))
            print('Текст: \n', row.message_text, '\n')

        # классификация
        try:
            # answer = predictor.classify(data=row)
            short_answer, answer = predictor.predict(data=str(row.message_title + row.message_text))
        except Exception as e:
            if args.debug:
                print("predictor.classify(). Ошибка классфикации для записи. MSGID: {}, ID: {}".format(row.message_id, row.id))
                print(str(e))
        else:
            if args.debug:
                print("Категория: {}".format(answer))
                print('*'*100,'\n')

            # Обновляем запись в clearDB
            try:
                row.isclassified = 1
                row.category = answer
                session.commit()
            except Exception as e:
                if args.debug:
                    print("ERROR. Ошибка обновления записи в ClearDB. MSGID: {}, ID: {}".format(row.message_id, row.id))
            else:
                # Добавлем запись в таблицу train_api для работы API и функции переобучения
                try:
                    new = TrainAPIRecords()
                    new.uuid = uuid.uuid4().__str__()
                    new.message_id = row.message_id
                    new.auto_cat = short_answer
                    new.category = answer
                    new.date = datetime.datetime.now()
                    new.user_action = 0
                    new.user_answer = ""
                    new.train_epoch = CURRENT_TRAIN_EPOCH
                    session.add(new)
                    session.commit()
                except Exception as e:
                    if args.debug:
                        print("predictor.classify(). Ошибка записи в TRAIN_API. {}".format(str(e)))

    # обновляем статистику после классификации
    """
    if clear and CPO.PRODUCTION_MODE:
        if args.debug:
            print("predictor.classify(). Считаем дневную статистику по основным показателям.")
        try:
            CPO.violation_stat_daily()
        except Exception as e:
            print("predictor.classify(). Ошибка вычисления статистики. {}".format(str(e)))
    else:
        print("*** Система находится в режиме обучения ***")
        print("*** Статистика не рассчитывается ***")
        print("clear:", type(clear))
        print("PRODUCTION_MODE: ", CPO.PRODUCTION_MODE)
    """

finally:
    session.close()

