#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import re
import email
from email.header import Header
from smtplib import SMTP_SSL, SMTP
import datetime
import pdfkit
import uuid

from mako.lookup import TemplateLookup
lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")


def send_email(category=None, orig_msg=None, msg_uuid=None):
    """
    Отправка оповещений на адрес отправителя с результатами классификации.

    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = "test@agava.local"

    # Получаем список адресов для отправки уведомления
    to_addr = re.split("\\s", "vipct@conparser.vipservice.ru")


    body = "Письмо было проанализовано. \n"

    msg.preamble = "This is a multi-part message in MIME format."
    msg.epilogue = "End of message"

    f = open("/home/sergey/Downloads/_978803ada596ebb23988fe6406c5c7ec_Osnovy-matematicheskogo-analiza.pdf", "r")
    pdf = f.read()
    part = email.MIMEBase.MIMEBase('application', "octet-stream")
    part.set_payload(pdf)
    email.Encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="attach.pdf"')
    msg.attach(part)
    f.close()

    # PLAIN text сообщение
    msg.attach(email.MIMEText.MIMEText(body, "plain", "UTF-8"))


    smtp = SMTP()

    try:
        smtp.connect("192.168.0.104", port=25)
        # smtp.login(from_addr, smtp_pass)
    except Exception as e:
        print "Ошибка подключения к серверу %s с логином %s."  % ("", from_addr)
        print "Ошибка: ", str(e)
    else:
        msg['message-id'] = uuid.uuid4().__str__()
        msg['Date'] = datetime.datetime.now().__str__() + " +0300"
        # msg['From'] = from_addr
        msg['From'] = "wsd55cfuh@reshim.com"
        msg['To'] = ""
        msg['Subject'] = Header("Сообщение от Conversation parser", "utf8")

        for addr in to_addr:
            # msg.replace_header("To", "golubkov@vipct.ru")
            msg.replace_header("To", "tttry333y@geoprice.mobi")
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


for i in range(7000):
    send_email()

