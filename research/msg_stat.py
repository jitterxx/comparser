#!/usr/bin/python -t
# coding: utf8

__author__ = 'Sergey Fomin'

import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['/home/sergey/dev/conflict analyser'])

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import and_, or_
from configuration import *
import datetime
import uuid
import re
from dateutil.parser import *
import objects as CPO


class stat(object):
    thread_uuid = None
    message_id = None
    create_date = None

    def __init__(self):
        self.message_id = ""
        self.thread_uuid = None
        self.create_date = None

session = CPO.Session()

id_list = [1273, 1278, 1287, 1291, 11314, 1360, 1458, 2081, 2092, 2126, 2128, 176, 177, 192, 201, 851, 889]
raw_msg = session.query(CPO.MsgRaw).filter(and_(CPO.MsgRaw.orig_date_str != "",
                                                #CPO.MsgRaw.id.in_(id_list),
                                                CPO.MsgRaw.orig_date_str != "")).all()

raw = dict()
raw_ref = dict()
stats = dict()
msg_to_tread = dict()
treads = dict()

from dateutil.parser import *
from dateutil.tz import tzutc, tzlocal


for msg in raw_msg:
    raw[msg.message_id] = msg
    raw_ref[msg.message_id] = list()
    if msg.references:
        for one in re.split("\s+|[,]\s+", str(msg.references)):
            if one:
                raw_ref[msg.message_id].append(one)

    try:
        orig_date_utc = parse(msg.orig_date_str).astimezone(tzutc()).replace(tzinfo=None)
    except Exception as e:
        print "MSGID: ", msg.message_id
        print "Create date: ", msg.orig_date_str
        print "Ошибка считывания времени в UTC. %s" % str(e)
        orig_date_utc = None
        raw_input()

    stats[msg.message_id] = orig_date_utc

    print "MSGID: ", msg.message_id
    print "Create date: ", msg.orig_date_str
    print "Create date UTC: ", orig_date_utc
    print "References: ", raw_ref[msg.message_id]
    print "In-Reply-To: ", msg.in_reply_to
    print "-" * 30
    # raw_input()

"""
for msg in raw_msg:

    if not msg.references and not msg.in_reply_to:
        # Если Reference и InReplyTo пустые - это первое сообщение в треде, создаем новый тред
        new_id = uuid.uuid4().__str__()
        msg_to_tread[msg.message_id] = new_id
        treads[new_id] = list()
        treads[new_id].append(msg.message_id)
    elif msg.in_reply_to:
        # Если поле InReplyTo не пустое, ищем сообщение по MSGID из него и тред в которое оно попадает
        if msg.in_reply_to in msg_to_tread.keys():
            # Родительское сообщение найдено в тредах.
            # Присваиваем ИД родительского треда новому сообщению
            cur_id = msg_to_tread[msg.in_reply_to]
            msg_to_tread[msg.message_id] = cur_id
            treads[cur_id].append(msg.message_id)
        else:
            # Если поле InReplyTo не пустое и родительского сообщения нет в raw (возможно оно пропущено),
            # то ищем в поле Reference у других сообщений
            for ref in raw_ref:
                if msg.in_reply_to in ref:
"""


for msg in raw_msg:
    """
    # Ищем в уже существующих сообщениях вхождения из References для нового
    if raw_ref[msg.message_id]:
        in_ref = False
        for one in raw_ref[msg.message_id]:
            if one in msg_to_tread.keys():
                # найдено вхождение из References в какой-то тред, помечаем сообщение его кодом
                msg_to_tread[msg.message_id] = msg_to_tread[one]
                treads[msg_to_tread[one]].append(msg.message_id)
                in_ref = True
        if not in_ref:
            # ни одно сообщение из References не было найдено в тредах, создаем новый тред
            id = uuid.uuid4().__str__()
            # Добавляем в новый тред само сообщение
            msg_to_tread[msg.message_id] = id
            treads[id] = list()
            treads[id].append(msg.message_id)
            # Добавлем все его References
            for one in raw_ref[msg.message_id]:
                msg_to_tread[one] = id
                treads[id].append(one)

    else:
        # если сообщение не имеет References и InReplyTo, то считаем его новым (первым в треде)
        id = uuid.uuid4().__str__()
        msg_to_tread[msg.message_id] = id
        treads[id] = list()
        treads[id].append(msg.message_id)

    """

    if msg.message_id not in msg_to_tread.keys():
        tread_id = None
        new_ref = list()
        if raw_ref[msg.message_id] or msg.in_reply_to:
            # Формируем список для поиска
            if msg.in_reply_to and raw_ref[msg.message_id]:
                if msg.in_reply_to in raw_ref[msg.message_id]:
                    ref = raw_ref[msg.message_id]
                else:
                    ref = raw_ref[msg.message_id] + [msg.in_reply_to]
            elif msg.in_reply_to and not raw_ref[msg.message_id]:
                ref = [msg.in_reply_to]
            elif not msg.in_reply_to and raw_ref[msg.message_id]:
                ref = raw_ref[msg.message_id]

            # Ищем для сообщения существующий код треда по msg-id в references и in-reply-to
            tread_id = None
            for one in ref:
                if one in msg_to_tread.keys():
                    # запоминаем код треда
                    tread_id = msg_to_tread[one]
                else:
                    # если сообщение не обрабатывалось, запоминаем его для обработки
                    new_ref.append(one)

            # если корд треда найден
            if tread_id:
                # Записываем в тред само сообщение
                msg_to_tread[msg.message_id] = tread_id
                treads[tread_id].append(msg.message_id)
            # если код не найден, то это новое сообщение в новом треде
            else:
                # Создаем новый тред
                tread_id= uuid.uuid4().__str__()
                # Записываем в тред само сообщение
                msg_to_tread[msg.message_id] = tread_id
                treads[tread_id] = list()
                treads[tread_id].append(msg.message_id)

            # Записываем в тред все новые msg_id из references и in-reply-to
            for one in new_ref:
                msg_to_tread[one] = tread_id
                treads[tread_id].append(one)

        else:
            # если в сообщении   пустые References и InReplyTo, то считаем его новым (первым в треде)
            # Иногда это не так и надо искать другими методами (например, по полю Тема)
            new_id = uuid.uuid4().__str__()
            msg_to_tread[msg.message_id] = new_id
            treads[new_id] = list()
            treads[new_id].append(msg.message_id)


    # print "MSG TO TREAD: ", msg_to_tread
    # print "TREADS: ", treads
    # print "*" * 30

    pass
    CPO.add_message_to_thread(msg=msg)


print "Всего сообщений: ", len(msg_to_tread.keys())
print "Всего тредов: ", len(treads.keys())
max1 = ["", 0]
# Длина и время треда
tread_stat = dict()

for one in treads.keys():

    tread_stat[one] = [None, None]
    # Ищем максимум
    if len(treads[one]) > max1[1]:
        max1[1] = len(treads[one])
        max1[0] = one
    # Считаем длинну треда
    t_len = len(treads[one])
    tread_stat[one][0] = t_len

    # print "Тред: ", one
    # print "Длина треда: ", tread_stat[one][0]

    # """
    print "Сообщения треда: "
    for t in treads[one]:
        if t in raw.keys():
            print "\t", t, " - ", raw.get(t).message_title, " - ", stats[t]
        else:
            print "\t", t
    # """

    # Считаем время треда
    # Надо взять время создания первого сообщения и последнего, посчитать разницу
    start = None
    end = None
    try:
        """
        if treads[one][0] in raw.keys():
            start = stats.get(treads[one][0])
            if treads[one][t_len - 1] in raw.keys():
                end = stats.get(treads[one][t_len - 1])
                print start, " -> ", end
                tread_stat[one][1] = end - start
        """
        ref = treads[one]
        # поиск первого сообщения с временем
        for m in ref:
            start = stats.get(m)
            if start:
                break

        # поиск последнего сообщения с временем
        ref.reverse()
        for m in ref:
            end = stats.get(m)
            if end:
                break

        print start, " -> ", end

        if start and end:
            tread_stat[one][1] = end - start

    except Exception as e:
        pass
    else:
        print "Время треда: ", tread_stat[one][1]
        print "Время/кол-во сообщений: ", tread_stat[one][1]/t_len
        pass
    finally:
        print "*" * 30
        # raw_input()
        pass


"""
print "Самый длинный тред: %s" % max1[1]
for one in treads[max1[0]]:
    if one in raw.keys():
        print "\t", one, " - ", raw.get(one).message_title, " - ", stats[one]
    else:
        print "\t", one

print tread_stat[max1[0]]
"""

print "Статистика"

sum = 0
count = 0
raspred = dict()
sum_t = datetime.timedelta()

for one in treads.keys():
    if 2 <= len(treads[one]) <= 50:
        sum += len(treads[one])
        count += 1
        sum_t = sum_t + tread_stat[one][1]
        if len(treads[one]) in raspred.keys():
            raspred[len(treads[one])] += 1
        else:
            raspred[len(treads[one])] = 1

print "Распределение тредов: "
for num, val in raspred.iteritems():
    print "\t - %s  - %s " % (num, val)

print "Средняя длинна: ", float(sum)/count
print "Среднее время: ", sum_t/count


session.close()

