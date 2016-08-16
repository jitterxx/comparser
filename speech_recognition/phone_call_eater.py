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
        print "Ошибка получения записей о звонках. {0}".format(str(e))
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


def get_phone_calls(provider=None, from_date=None, to_date=None, offset=0):
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
            parameters = {"api_key": PHONE_API_KEY, "max": 100, "change_date": change_date, "offset": offset,
                          "from_date": change_date}
            print "req params: ", parameters
        elif from_date and to_date is None:
            parameters = {"api_key": PHONE_API_KEY, "max": 100, "change_date": from_date, "offset": offset,
                          "from_date": from_date}
            print "req params: ", parameters
        req = requests.get(url=url, params=parameters)
        while True:
            print "status :", req.status_code
            if req.status_code in [200, 304]:
                break
            else:
                time.sleep(10)
                print "Ждем 10 сек..."

        if req.status_code == 200:
            print req.content
            return json.loads(req.content)
        else:
            return []


    else:
        return ""




if __name__ == "__main__":

    call_list = list()
    calls = get_phone_calls(provider="callmart", offset=0)

    try:
        os.makedirs(PHONE_CALL_TEMP)
    except Exception as e:
        print str(e)


    if calls:
        print "Calls: ", len(calls.get("data").get("list"))
        session = CPO.Session()
        for one in calls.get("data").get("list"):

            file_name = ""
            if one["recordUrl"] is not None:
                file_name = "{}/{}_{}_{}.mp3".format(PHONE_CALL_TEMP, one["id"], one["phoneFrom"], one["phoneTo"])

            # Время приводим к МСК
            try:
                dt = parse(one["dateCreated"]).astimezone(tzlocal()).replace(tzinfo=None)
            except Exception as e:
                print "phone_call_eater. Ошибка считывания времени {} из сообщения. \n " \
                      "Ошибка: {}".format(one["dateCreated"], str(e))
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
                    print "Не указано имя звонившего, ID - {}".format(one["id"])
                    new.from_name = ""

                try:
                    new.to_name = one["user"]["name"]
                except KeyError as e:
                    print "Не указано имя ответившего, ID - {}".format(one["id"])
                    new.to_name = ""

                new.call_date = dt
                new.duration = one["duration"]
                new.record_link = one["recordUrl"]
                new.record_file = file_name
                new.create_date = datetime.datetime.now()
                new.references = ""
                new.is_cleared = 0

                print "Обрабатываю звонок ID: {0}".format(one["id"])
                print "Статус: ", one["phoneStatus"]
                print "От кого: ", one["phoneTo"]
                print "Кому: ", one["phoneFrom"]
                print "Длительность: ", one["duration"]
                print "Время: ", one["dateCreated"]
                print "Имя звонившего: ", new.from_name
                print "Имя ответившего: ", new.to_name
                print "Ссылка на запись: ", one["recordUrl"]
                print "Имя файла: {}_{}_{}".format(one["id"], one["phoneFrom"], one["phoneTo"])
                print "*"*30

                session.add(new)
                session.commit()
            except exc.IntegrityError as e:
                print "Запись с таким ID={} уже существует."
                print "*"*30
                raw_input("Нажмите клавишу")
                session.rollback()
            except Exception as e:
                print "Ошибка при записи данныех звонка ID-{}. Ошибка: {}".format(one["id"], str(e))
                raw_input("Звоннок НЕ записан... Нажмите клавишу")
            else:
                if one["recordUrl"] is not None:
                    with open(file_name, 'wb') as f:
                        r = requests.get(url=one["recordUrl"], stream=True)
                        print "Записываем данные в файл {}".format(file_name)
                        for block in r.iter_content(1024):
                            if not block:
                                print "Файл скачан."
                                break
                            f.write(block)

                raw_input("Звоннок записан... Нажмите клавишу")

        session.close()


