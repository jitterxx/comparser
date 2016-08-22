#!/usr/bin/python -t
# coding: utf8


# import email.parser, email.utils
# import chardet
# import base64
# import html2text
# import MySQLdb
# import datetime


import mailbox

import poplib, email
import re
import argparse
import logging
from configuration import *

# conversation parser object
import objects as CPO
from sqlalchemy import exc
import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


parser = argparse.ArgumentParser(description='Debug option')
parser.add_argument('-d', action='store_true', dest='debug', help='print debug info')
args = parser.parse_args()
debug = True

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s in \'%(module)s\' at line %(lineno)d: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=logging.DEBUG,
                    filename='{}/{}.log'.format(os.path.expanduser("~"), os.path.basename(sys.argv[0])))


data = ""

data = sys.stdin

msg = email.message_from_file(data)

if msg:
    session = CPO.Session()
    try:
        message = CPO.parse_message(msg=msg, debug=debug)
        if debug:
            logging.debug("\n# Оригинальные поля сообщения")
            logging.debug("ID: {}".format(str(message[0])))
            logging.debug("Date: {}".format(str(message[7])))
            logging.debug("From: {} \n To: {}".format(str(message[1]), str(message[2])))
            logging.debug("Subject: {}".format(msg.get('Subject', 'No subject provided')))

        new = CPO.MsgRaw()
        new.message_id = message[0]  # msg_id
        new.sender = message[1]  # from_
        new.recipient = message[2]  # to
        new.cc_recipient = message[3]  # cc
        new.message_title = message[4]  # subject
        new.message_text = message[5]  # text2[0]
        new.message_text_html = message[6]  # text2[1]
        new.orig_date = message[7]  # msg_datetime
        new.isbroken = message[8]  # int(broken_msg)
        new.references = message[9]  # references
        new.in_reply_to = message[10]  # in-reply-to header
        new.orig_date_str = message[11]  # original date header string with timezone info

        # TODO: Ошибка при обработке некоторых сообщений и записи данных в базу.
        # Из-за ошибки записи, сообщение не считается принятым и при каждом подключении принимается getmail снова
        """
            Incorrect string value: '\xCE\xBB, \xCF\x86...' for column 'raw_body' at row 1 #21
            http://stackoverflow.com/questions/1168036/how-to-fix-incorrect-string-value-errors

            Обходной вариант решения, уд

        """

        session.add(new)
        session.commit()
    except exc.IntegrityError as e:
        logging.error("Запись с таким Message-ID={} уже существует.".format(new.message_id))
        logging.error("*"*30)
        session.rollback()
        sys.exit(100)
    except exc.OperationalError as e:
        logging.error("Operational Error. MID={}.".format(new.message_id))
        logging.error("{}".format(str(e)))
        logging.error("*"*30)

        session.rollback()
        sys.exit(100)

    except Exception as e:
        logging.error("Message ID: %s" % msg['message-id'])
        logging.error("Ошибка записи нового сообщения. %s" % str(e))
        logging.error("*"*30)
        sys.exit(100)
    else:
        if debug:
            logging.debug("*"*30)
            # print 'Перенос в прочитанные...\n'
            # print 'Битое: ', message[8]
            pass
    finally:
        session.close()

# print msg

# если все нормально, фильтр завершает работу с кодом 100, чтобы getmail дропнул сообщение и
# не доставлял в майлбокс
# sys.exit(os.EX_OK)
sys.exit(100)

