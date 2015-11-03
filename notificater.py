#!/usr/bin/python -t
# coding: utf8

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from configuration import *
import re
import email
from email.header import Header
from smtplib import SMTP_SSL

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'

sql_uri = "mysql://%s:%s@%s/clear_data?charset=utf8" % (db_user, db_pass, db_host)

Base = declarative_base()
Engine = sqlalchemy.create_engine(sql_uri, pool_size=20)
Session = sqlalchemy.orm.sessionmaker(bind=Engine)

"""
1. Читаем результаты классификации из базы
2. Если классификация попадает в условия, то формируем сообщение в адрес менеджера
"""


class Msg(Base):

    __tablename__ = "email_cleared_data"

    id = Column(sqlalchemy.Integer, primary_key=True)
    message_id = Column(sqlalchemy.String(256))
    sender = Column(sqlalchemy.String(256))
    sender_name = Column(sqlalchemy.String(256))
    recipients = Column(sqlalchemy.TEXT())
    recipients_name = Column(sqlalchemy.TEXT())
    cc_recipients = Column(sqlalchemy.TEXT())
    cc_recipients_name = Column(sqlalchemy.TEXT())
    message_title = Column(sqlalchemy.TEXT())
    message_text = Column(sqlalchemy.TEXT())
    orig_date = Column(sqlalchemy.DATETIME())
    create_date = Column(sqlalchemy.DATETIME())
    isclassified = Column(sqlalchemy.Integer)
    category = Column(sqlalchemy.String(256))


def notify():
    session = Session()

    query = session.query(Msg).filter(Msg.isclassified == 1).all()
    for msg in query:
        category = dict()
        cats = re.split(":", msg.category)
        l = dict()
        for cat in cats:
            m = re.split("-", cat)
            l[m[0]] = float(m[1])

        category[msg.id] = l

        if category[msg.id]['normal'] >= 0.7:
            print category[msg.id]
            send_email(l, msg)

    session.close()


def send_email(category, orig_msg):
    """
    Отправка оповещений на адрес отправителя с результатами классификации.

    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = "comparser@reshim.com"
    to_addr = orig_msg.sender

    orig_text = "\n\n---------------- Исходное сообщение -------------------\n"
    orig_text += "От кого: %s (%s)\n" % (orig_msg.sender_name, orig_msg.sender)
    orig_text += "Кому: %s (%s) \n" % (orig_msg.recipients_name, orig_msg.recipients)
    orig_text += "Тема: %s" % orig_msg.message_title
    orig_text += "%s" % orig_msg.message_text
    orig_text += "\n------------------------------------------------------\n"

    text = "Категории: \n"
    for cat in category.keys():
        text += "\t %s - %.2f%% \n" % (cat, category[cat])

    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = Header("Сообщение от Communication parser", "utf8")
    body = "Проверочное письмо \n" + text + orig_text
    msg.preamble = "This is a multi-part message in MIME format."
    msg.epilogue = "End of message"

    msg.attach(email.MIMEText.MIMEText(body, "plain", "UTF-8"))

    smtp = SMTP_SSL()
    smtp.connect("smtp.gmail.com")
    smtp.login("comparser@reshim.com", "Cthutq123")
    text = msg.as_string()
    smtp.sendmail(from_addr, to_addr, text)
    smtp.quit()


notify()