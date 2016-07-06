#!/usr/bin/python -t
# coding: utf8

# import sqlalchemy
# from sqlalchemy import Table, Column, Integer, ForeignKey
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy import and_
# from configuration import *
import datetime
import email
from email.header import Header
from smtplib import SMTP_SSL
# from mod_classifier import fisherclassifier, specfeatures #  старые функции классификации для старого демо
# import uuid
# import re

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'


def landing_customer_contacts(customer_email=None, customer_phone=None, customer_name=None, customer_session=None,
                              pd=None, ads_code=None):
    """
    Функция отправки контактных данных полученных с лендинга.

    :param customer_email:
    :param customer_phone:
    :param customer_name:
    :param customer_session:
    :param pd: соглашение о перс данных
    :param ads_code: код объявления
    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = "info@conparser.ru"
    smtp_server = "smtp.yandex.ru"
    #to_addr = "sergey@reshim.com, ramil@reshim.com"
    to_addr = "sergey@reshim.com"

    msg['From'] = from_addr
    msg['To'] = to_addr
    text = "\tИмя: %s \n" % customer_name
    text += "\tE-mail: %s \n\tТелефон: %s \n" % (customer_email, customer_phone)
    text += "\tОтметка об обработке персональных данных: %s \n" % pd
    text += "\tДата и время: %s \n" % datetime.datetime.now()
    text += "\tКод объявления: %s \n" % str(ads_code)
    text += "Параметры сессии: \n "
    for a,b in customer_session.items():
        text += "\t%s : %s \n" % (a, b)

    msg['Subject'] = Header("Контакты с лендинга Conversation parser", "utf8")
    body = "Оставлены контакты. \n" + text
    msg.preamble = "This is a multi-part message in MIME format."
    msg.epilogue = "End of message"

    msg.attach(email.MIMEText.MIMEText(body, "plain", "UTF-8"))

    smtp = SMTP_SSL()
    smtp.connect(smtp_server)
    smtp.login(from_addr, "Cthutq123")
    text = msg.as_string()
    smtp.sendmail(from_addr, to_addr.split(","), text)
    smtp.quit()

