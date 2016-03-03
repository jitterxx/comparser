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
from configuration import *

# conversation parser object
import objects as CPO

import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


parser = argparse.ArgumentParser(description='Debug option')
parser.add_argument('-d', action='store_true', dest='debug', help='print debug info')
args = parser.parse_args()
debug = args.debug

data = ""

data = sys.stdin

msg = email.message_from_file(data)

if msg:
    try:
        session = CPO.Session()

        message = CPO.parse_message(msg=msg, debug=debug)

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

        session.add(new)
        session.commit()
    except Exception as e:
        print "Ошибка записи нового сообщения. %s" % str(e)
        print "Message ID: %s" % msg['message-id']
        sys.exit(os.EX_DATAERR)
    else:
        if debug:
            print 'Перенос в прочитанные...\n'
            print 'Битое: ', message[8]
        sys.exit(os.EX_OK)
    finally:
        session.close()



