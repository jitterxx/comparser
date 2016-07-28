#!/usr/bin/python -t
# coding: utf8

"""
Импорт данных в тренировочную базу из xls

"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.append("..")

import xlrd
import re
import datetime
from configuration import *
import objects as CPO
import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey, and_
from sqlalchemy.ext.declarative import declarative_base
import uuid


if __name__ == "__main__":
    sql_uri = "mysql://%s:%s@%s:%s/%s?charset=utf8" % (db_user, db_pass, db_host, db_port, db_name)

    xls_file = "demo_data.xlsx"

    CPO.create_tables()

    # Открываем файл
    rb = xlrd.open_workbook(xls_file)

    session = CPO.Session()

    # Добавляем вспомогательные данные (пользователи, наблюдатели и тд)
    user = CPO.User()
    user.name = "Елена"
    user.surname = "(контроль качества)"
    user.login = "elena"
    user.password = "demopass"
    user.email = "info@conparser.ru"
    user.access_groups = "admin,users"
    user.status = 0
    user.uuid = "demo-service-uuid"
    session.add(user)
    session.commit()

    # Добавляем категории
    category = CPO.Category()
    category.code = "conflict"
    category.category = "Обратить внимание"
    session.add(category)
    session.commit()

    category = CPO.Category()
    category.code = "normal"
    category.category = "Нейтральное"
    session.add(category)
    session.commit()

    # ФИО участников переписки
    names = dict()

    sheet = rb.sheet_by_index(0)
    for rownum in range(1, sheet.nrows):
        # Если это сотрудник
        if sheet.cell_value(rowx=rownum, colx=0) == "employee":
            names[str(sheet.cell_value(rowx=rownum, colx=2))] = str(sheet.cell_value(rowx=rownum, colx=3)) + \
                                                                str(sheet.cell_value(rowx=rownum, colx=4))
            names[str(sheet.cell_value(rowx=rownum, colx=1))] = str(sheet.cell_value(rowx=rownum, colx=3)) + \
                                                                str(sheet.cell_value(rowx=rownum, colx=4))

            CPO.create_dialog_member(name=sheet.cell_value(rowx=rownum, colx=3),
                                     surname=sheet.cell_value(rowx=rownum, colx=4),
                                     m_type=0,
                                     emails=str(sheet.cell_value(rowx=rownum, colx=2)),
                                     phone=str(sheet.cell_value(rowx=rownum, colx=1)))
        # это клиент
        elif sheet.cell_value(rowx=rownum, colx=0) == "client":
            cli_name = "Клиент " + str(rownum)
            names[str(sheet.cell_value(rowx=rownum, colx=2))] = cli_name
            names[str(sheet.cell_value(rowx=rownum, colx=1))] = cli_name
            CPO.create_dialog_member(name=cli_name,
                                     surname="",
                                     m_type=1,
                                     emails=str(sheet.cell_value(rowx=rownum, colx=2)),
                                     phone=str(sheet.cell_value(rowx=rownum, colx=1))
                                     )
        # это домен для наблюдения
        elif sheet.cell_value(rowx=rownum, colx=0) == "check_domain":

            mrk = CPO.WatchMarker()
            mrk.channel_type = 0
            mrk.client_marker = sheet.cell_value(rowx=rownum, colx=1)
            mrk.user_uuid = "demo-service-uuid"

            session.add(mrk)
            session.commit()

        # это телефон для наблюдения
        elif sheet.cell_value(rowx=rownum, colx=0) == "check_phone":

            mrk = CPO.WatchMarker()
            mrk.channel_type = 1
            mrk.client_marker = sheet.cell_value(rowx=rownum, colx=1)
            mrk.user_uuid = "demo-service-uuid"

            session.add(mrk)
            session.commit()

        else:
                pass

    print names
    print "Вспомогательные данные загружены."
    raw_input()


    for i in range(1, 6):
        sheet = rb.sheet_by_index(i)
        # print sheet
        for rownum in range(1, sheet.nrows):
            # если не пустая строка
            if sheet.cell_value(rowx=rownum, colx=0):
                dialog_date = datetime.datetime(*xlrd.xldate_as_tuple(sheet.cell_value(rowx=rownum, colx=0), rb.datemode))
                print dialog_date

                # остальные данные
                cell = sheet.cell_value(rowx=rownum, colx=1)
                try:
                    raw = CPO.MsgRaw()
                    clear = CPO.Msg()
                    train = CPO.TrainAPIRecords()

                    # Raw message
                    raw.message_id = sheet.cell_value(rowx=rownum, colx=7)
                    raw.sender = sheet.cell_value(rowx=rownum, colx=1)
                    raw.recipient = sheet.cell_value(rowx=rownum, colx=3)
                    raw.cc_recipient = "empty"
                    raw.message_title = sheet.cell_value(rowx=rownum, colx=5)
                    raw.message_text = sheet.cell_value(rowx=rownum, colx=6)
                    raw.message_text_html = sheet.cell_value(rowx=rownum, colx=6)
                    raw.isbroken = 0
                    raw.iscleared = 1
                    raw.orig_date = dialog_date
                    raw.create_date = dialog_date
                    raw.orig_date_str = dialog_date.strftime("%a, %d %b %Y %H:%M:%S") + " +0300"
                    raw.in_reply_to = sheet.cell_value(rowx=rownum, colx=9)
                    raw.references = sheet.cell_value(rowx=rownum, colx=8)

                    session.add(raw)

                    clear.message_id = sheet.cell_value(rowx=rownum, colx=7)
                    clear.sender = sheet.cell_value(rowx=rownum, colx=1)
                    clear.sender_name = names.get(sheet.cell_value(rowx=rownum, colx=1))
                    clear.recipients = sheet.cell_value(rowx=rownum, colx=3)
                    clear.recipients_name = names.get(sheet.cell_value(rowx=rownum, colx=3))
                    clear.cc_recipients = "empty"
                    clear.cc_recipients_name = ""
                    clear.message_title = sheet.cell_value(rowx=rownum, colx=5)
                    clear.message_text = sheet.cell_value(rowx=rownum, colx=6)
                    clear.create_date = dialog_date
                    clear.orig_date = dialog_date
                    clear.isclassified = 1
                    clear.category = str(sheet.cell_value(rowx=rownum, colx=10)) + "-1.0:default-0"
                    clear.notified = 1
                    clear.references = sheet.cell_value(rowx=rownum, colx=8)
                    clear.in_reply_to = sheet.cell_value(rowx=rownum, colx=9)

                    session.add(clear)

                    # train API records
                    train.uuid = uuid.uuid4().__str__()
                    train.message_id = sheet.cell_value(rowx=rownum, colx=7)
                    train.train_epoch = 0
                    train.auto_cat = sheet.cell_value(rowx=rownum, colx=10)
                    train.date = dialog_date
                    train.user_action = 0
                    train.user_answer = ""
                    train.category = str(sheet.cell_value(rowx=rownum, colx=10)) + "-1.0:default-0"

                    session.add(train)

                    session.commit()

                    CPO.add_message_to_thread(msg=raw)
                    CPO.add_msg_members(msg_id_list=raw.message_id)

                except Exception as e:
                    print str(e)
                    raise e
        print "День %s записан." % (17 + i)
        raw_input()

    session.close()
