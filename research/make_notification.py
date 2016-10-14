#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from configuration import *
from objects import *
import re
import email
from email.header import Header
from smtplib import SMTP_SSL
import datetime
import pdfkit
from sqlalchemy import and_, or_
sys.path.extend(['..'])

from mako.lookup import TemplateLookup
lookup = TemplateLookup(directories=["../templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")

__author__ = 'sergey'

"""
1. Читаем результаты классификации из базы
2. Если классификация попадает в условия, то формируем сообщение в адрес менеджера
"""

CATEGORY = GetCategory()
code1, code2 = CATEGORY.keys()

# Инициализация переменных и констант
try:
    initial_configuration()
except Exception as e:
    print "Notificater(). Ошибка чтения настроек CPO.initial_configuration(). %s" % str(e)
    raise e


category = CATEGORY


class orig_msg:
    sender_name = "Sergey Fomin"
    sender = "sergey_fomin@list.ru"
    recipients = "Support <support@conparser.ru>"
    recipients_name = ""
    orig_date = "17:35 06-10-2016"
    message_title = "Re: Акты за выполненные работы"
    message_text = """

Добрый день,Иван.

Акты подписывать не будем. Ваш инженер не доделал работу, оборудование стоит разобранное.
Он сказал, что не хватает запчастей.
Иван, это уже не в первый раз происходит. Почему опять мы остались без работающего оборудования?
Давайте как-то решать этот вопрос.

С оплатой тоже самое, сначала выполните работы до конца.


 """

msg_uuid = "556366378393"
notify_list = ['info@conparser.ru']

"""
Отправка оповещений на адрес отправителя с результатами классификации.

:return:
"""

msg = email.MIMEMultipart.MIMEMultipart()
from_addr = smtp_email

# Получаем список адресов для отправки уведомления
# to_addr = re.split("\\s", to_address)
to_addr = notify_list

msg.preamble = "This is a multi-part message in MIME format."
msg.epilogue = "End of message"

# HTML сообщение
tmpl = lookup.get_template("email_notification.html")
body_in_html = tmpl.render(main_link=main_link, cat_list=CATEGORY, cat="conflict", orig_msg=orig_msg,
                           msg_uuid=msg_uuid, code1=code1, code2=code2)

msg.attach(email.MIMEText.MIMEText(body_in_html, "html", "UTF-8"))
print "Сообщение сформировано."

# PLAIN text сообщение
# msg.attach(email.MIMEText.MIMEText(body, "plain", "UTF-8"))

smtp = SMTP_SSL()

try:
    from_addr = 'info@conparser.ru'
    smtp_server = 'smtp.yandex.ru'
    smtp.connect(smtp_server)
    smtp.login(from_addr, 'Cthutq123')
except Exception as e:
    print "Ошибка подключения к серверу %s с логином %s."  % (smtp_server, from_addr)
    print "Ошибка: ", str(e)
else:
    msg['From'] = from_addr
    msg['To'] = ""
    msg['Subject'] = Header("Сообщение от Conversation parser", "utf8")
    for addr in to_addr:
        msg.replace_header("To", addr)
        text = msg.as_string()
        try:
            smtp.sendmail(from_addr, addr, text)
        except Exception as e:
            print "Ошибка отправки сообщения на адрес: %s " % addr
            print str(e)
        else:
            print "Отправленно на адрес: %s" % addr
finally:
    smtp.quit()


