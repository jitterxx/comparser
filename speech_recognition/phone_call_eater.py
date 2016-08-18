#!/usr/bin/python -t
# coding: utf8

"""
Скрипт извлекает звонки из телефонных систем, записывает их параметры в базу,
закачивает файлы с записями во временный каталог.
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import objects as CPO
from configuration import *
import datetime
import sqlalchemy
from sqlalchemy import func, exc
import requests
import time
import json
import os
from dateutil.parser import *
from dateutil.tz import tzutc, tzlocal
import logging

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s in \'%(module)s\' at line %(lineno)d: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=logging.DEBUG,
                    filename='{}/{}.log'.format(os.path.expanduser("~"), os.path.basename(sys.argv[0])))

def get_last_check_time():
    """
    Ищет в базе последнюю запись и берет время ее начала, за время последней проверки.
    Это необходимо что запрашивать в сервисе телефонии, только свежие записи.

    :return: datetime
    """
    session = CPO.Session()
    try:
        resp = session.query(func.max(CPO.PhoneCall.call_date)).all()
    except Exception as e:
        logging.error("Ошибка получения записей о звонках. {0}".format(str(e)))
        raise e
    else:
        if resp[0][0] is None:
            # Если записей нет, возвращает 00:00:00 текущего дня
            now = datetime.datetime.now()
            return datetime.datetime.strptime("{0}-{1}-{2} 00:00:00".format(now.day, now.month, now.year),
                                              "%d-%m-%Y %H:%M:%S")
        else:
            return resp[0][0]
    finally:
        session.close()


def get_phone_calls(provider=None, from_date=None, to_date=None, offset=0, max_res=1):
    """
    Функция получения записей от провайдера телефонии или станции.

    :param provider:
    :param from_date:
    :param to_date:
    :param offset:
    :return:
    """
    if provider == "callmart":
        parameters = {}
        url = "https://callmart.ru/api/1.0/call/list"

        if from_date is None and to_date is None:
            last_check = get_last_check_time()
            change_date = "{0}-{1:02d}-{2:02d} {3:02d}:{4:02d}:{5:02d}".\
                format(last_check.year, last_check.month, last_check.day,
                       last_check.hour, last_check.minute, last_check.second)
            parameters = {"api_key": PHONE_API_KEY, "max": max_res, "change_date": change_date, "offset": offset,
                          "from_date": change_date}
            logging.debug("req params: {}".format(parameters))
        elif from_date and to_date is None:
            parameters = {"api_key": PHONE_API_KEY, "max": max_res, "change_date": from_date, "offset": offset,
                          "from_date": from_date}
            logging.debug("req params: {}".format(parameters))
        req = requests.get(url=url, params=parameters)
        while True:
            logging.debug("status : {}".format(req.status_code))
            if req.status_code in [200, 304]:
                break
            else:
                time.sleep(10)
                logging.debug("Ждем 10 сек...")

        if req.status_code == 200:
            logging.debug("Ответ провайдера: {}".format(req.content))
            return json.loads(req.content)
        else:
            return []

    else:
        return ""


if __name__ == "__main__":

    logging.debug("####### Начало работы #########")

    try:
        request_limit = int(sys.argv[1])
    except Exception as e:
        logging.debug("Лимит не задан, используем стандартный - 10. {}".format(str(e)))
        request_limit = 10

    logging.debug("# Лимит количества обрабатываемых за один запуск разговоров: {}".format(request_limit))

    call_list = list()
    calls = get_phone_calls(provider="callmart", offset=0, max_res=request_limit)

    try:
        os.makedirs(PHONE_CALL_TEMP)
    except Exception as e:
        logging.debug("Каталог уже существует. {}".format(str(e)))


    if calls:
        logging.debug("Calls: {}".format(len(calls.get("data").get("list"))))
        session = CPO.Session()
        for one in calls.get("data").get("list"):

            # Работаем, если разговор уже завершен
            if one["phoneStatus"] == PHONE_CALL_STATUS_FOR_RECOGNIZE:

                # Проверяем номера на попадание в EXCEPTION и CHECK списки

                file_name = ""
                if one["recordUrl"] is not None:
                    file_name = "{}/{}_{}_{}.mp3".format(PHONE_CALL_TEMP, one["id"], one["phoneFrom"], one["phoneTo"])

                # Время приводим к МСК
                try:
                    dt = parse(one["dateCreated"]).astimezone(tzlocal()).replace(tzinfo=None)
                except Exception as e:
                    logging.error("phone_call_eater. Ошибка считывания времени {} из сообщения. \n " \
                                  "Ошибка: {}".format(one["dateCreated"], str(e)))
                    dt = parse(one["dateCreated"].split("+", 1)[0])


                try:
                    new = CPO.PhoneCall()
                    new.call_id = one["id"]
                    new.orig_call_id = one["id"]
                    new.call_status = one["phoneStatus"]
                    new.from_phone = one["phoneFrom"]
                    new.to_phone = one["phoneTo"]
                    try:
                        new.from_name = one["client"]["name"]
                    except KeyError as e:
                        logging.error("Не указано имя звонившего, ID - {}".format(one["id"]))
                        new.from_name = ""

                    try:
                        new.to_name = one["user"]["name"]
                    except KeyError as e:
                        logging.error("Не указано имя ответившего, ID - {}".format(one["id"]))
                        new.to_name = ""

                    new.call_date = dt
                    new.duration = one["duration"]
                    new.record_link = one["recordUrl"]
                    new.record_file = file_name
                    new.create_date = datetime.datetime.now()
                    new.references = ""
                    new.is_recognized = 0
                    new.recognize_uuid = ""

                    logging.debug("Обрабатываю звонок ID: {0}".format(one["id"]))
                    logging.debug("Статус: {}".format(one["phoneStatus"]))
                    logging.debug("От кого: {}".format(one["phoneTo"]))
                    logging.debug("Кому: {}".format(one["phoneFrom"]))
                    logging.debug("Длительность: {}".format(one["duration"]))
                    logging.debug("Время: {}".format(one["dateCreated"]))
                    logging.debug("Имя звонившего: {}".format(new.from_name))
                    logging.debug("Имя ответившего: {}".format(new.to_name))
                    logging.debug("Ссылка на запись: {}".format(one["recordUrl"]))
                    logging.debug("Имя файла: {}_{}_{}".format(one["id"], one["phoneFrom"], one["phoneTo"]))
                    logging.debug("*"*30)

                    session.add(new)
                    session.commit()
                except exc.IntegrityError as e:
                    logging.error("Запись с таким ID={} уже существует.")
                    logging.error("*"*30)
                    # raw_input("Нажмите клавишу")
                    session.rollback()
                except Exception as e:
                    logging.error("Ошибка при записи данныех звонка ID-{}. Ошибка: {}".format(one["id"], str(e)))
                    # raw_input("Звонок НЕ записан... Нажмите клавишу")
                else:
                    if one["recordUrl"] is not None:
                        with open(file_name, 'wb') as f:
                            r = requests.get(url=one["recordUrl"], stream=True)
                            logging.debug("Записываем данные в файл {}".format(file_name))
                            for block in r.iter_content(1024):
                                if not block:
                                    logging.debug("Файл скачан.")
                                    break
                                f.write(block)

                    # raw_input("Звонок записан... Нажмите клавишу")

        session.close()


        logging.debug("####### Завершение работы #########")