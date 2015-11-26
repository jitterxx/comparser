#!/usr/bin/python -t
# coding: utf8

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import and_
from configuration import *
from objects import *
import re
import email
from email.header import Header
from smtplib import SMTP_SSL

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'

"""
1. Читаем результаты классификации из базы
2. Если классификация попадает в условия, то формируем сообщение в адрес менеджера
"""

CATEGORY = GetCategory()
code1, code2 = CATEGORY.keys()


def notify():
    session = Session()

    query = session.query(Msg).filter(and_(Msg.isclassified == 1, Msg.notified == 0)).all()

    for msg in query:
        try:
            query1 = session.query(TrainAPIRecords).filter(TrainAPIRecords.message_id == msg.message_id).one()
        except Exception as e:
            print "Ошибка получения uuid для сообщения %s." % msg.message_id
            msg_uuid = ""
        else:
            msg_uuid = query1.uuid

        cats = re.split(":", msg.category)
        l = dict()
        for cat in cats:
            m = re.split("-", cat)
            if m[1] == "unknown":
                m[1] = 0
            l[m[0]] = float(m[1])

        category = sorted(l.items(), key=lambda (k, v): v, reverse=True)
        print "От: %s (%s)" % (msg.sender, msg.sender_name)
        print "\n%s\n" % msg.message_text
        print category
        send_email(category, msg, msg_uuid)
        msg.notified = 1
        session.commit()

        # Чистые сообщения используются для переобучения системы, если была совершена ошибка и пользователь об этом
        # сообщил. При отправке результатов не чистим.
        # session.delete(msg)
        # session.commit()

    session.close()


def send_email(category, orig_msg, msg_uuid):
    """
    Отправка оповещений на адрес отправителя с результатами классификации.

    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = from_email
    if to_email:
        to_addr = to_email
    else:
        to_addr = orig_msg.sender

    orig_text = "\n\n---------------- Исходное сообщение -------------------\n"
    orig_text += "От кого: %s (%s)\n" % (orig_msg.sender_name, orig_msg.sender)
    orig_text += "Кому: %s (%s) \n" % (orig_msg.recipients_name, orig_msg.recipients)
    orig_text += "Тема: %s" % orig_msg.message_title
    orig_text += "%s" % orig_msg.message_text
    orig_text += "\n------------------------------------------------------\n"

    text = "Результат: \n"
    cat, val = category[0]
    if val != 0:
        text += "\t %s - %.2f%% \n" % (CATEGORY[cat].category, val*100)
    else:
        text += "\t Затрудняюсь определить. \n"

    links_block = """\n
    Независимо от результата, укажите пожалуйста правильный вариант.
    Для этого перейдите по одной из ссылок: \n
        %s - %s
        %s - %s
    \n
    Ваш ответ будет использован для повышения точности анализа.
    \n
    Спасибо за участие,
    команда Conversation Parser.
    \n""" % (CATEGORY[code1].category, main_link + "%s/%s" % (msg_uuid, CATEGORY[code1].code),
             CATEGORY[code2].category, main_link + "%s/%s" % (msg_uuid, CATEGORY[code2].code))

    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = Header("Сообщение от Conversation parser", "utf8")
    body = "Отправленное вами описание было проанализовано. \n" + text + links_block + orig_text
    msg.preamble = "This is a multi-part message in MIME format."
    msg.epilogue = "End of message"

    msg.attach(email.MIMEText.MIMEText(body, "plain", "UTF-8"))

    smtp = SMTP_SSL()
    smtp.connect(smtp_server)
    smtp.login(from_addr, smtp_pass)
    text = msg.as_string()
    smtp.sendmail(from_addr, to_addr, text)
    smtp.quit()


notify()