#!/usr/bin/python -t
# coding: utf8


import mailbox
import email.parser, email.utils
import chardet
from email.header import decode_header
import poplib, email
import base64
import re
# import html2text
import MySQLdb
import datetime
from dateutil.parser import *
import argparse
from configuration import *
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

def line_decoder (text_line):
 s_text_line = text_line.split(" ")
 #print 'split: ',s_text_line
 #print 'Количество циклов: ',len(s_text_line)
 #print 'Пошел цикл...'+'\n'
 result=''

 for i in range (len(s_text_line)):
   #print 'Шаг номер ',i,':\n'
   data=''
   coding=''
   #print 'Split item & num: ',s_text_line[i], i,'\n'
   data, coding = decode_header(s_text_line[i])[0]
   #print 'Decoded data, coding: ',data, coding,'\n'
   if coding == None:
        result = result + ' ' + data
   else:
        result = result + data.decode(coding,'replace')
 #print 'Decoded data, coding: ',result, coding,'\n'
 return result



def get_decoded_email_body(message_body):
    """ Decode email body.

    Detect character set if the header is not set.

    We try to get text/plain, but if there is not one then fallback to text/html.

    :param message_body: Raw 7-bit message body input e.g. from imaplib. Double encoded in quoted-printable and latin-1

    :return: Message body as unicode string
    """

    msg = email.message_from_string(message_body)

    text = ""
    if msg.is_multipart():
        html = None
        for part in msg.get_payload():

            print "%s, %s" % (part.get_content_type(), part.get_content_charset())

            if part.get_content_charset() is None:
                # We cannot know the character set, so return decoded "something"
                text = part.get_payload(decode=True)
                continue

            charset = part.get_content_charset()

            if part.get_content_type() == 'text/plain':
                text = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

            if part.get_content_type() == 'text/html':
                html = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

        if text is not None:
            return text.strip()
        else:
            return html.strip()
    else:
        text = unicode(msg.get_payload(decode=True), msg.get_content_charset(), 'ignore').encode('utf8', 'replace')
        return text.strip()


# note that if you want to get text content (body) and the email contains
# multiple payloads (plaintext/ html), you must parse each message separately.
# use something like the following: (taken from a stackoverflow post)
def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
            return email_message_instance.get_payload()


def remove_tags(data):
    # remove the newlines
    data = data.replace("\n", " ")
    data = data.replace("\r", " ")

    # replace consecutive spaces into a single one
    data = " ".join(data.split())

    # get only the body content
    bodyPat = re.compile(r'<body[^<>]*?>(.*?)</body>', re.I)
    if re.findall(bodyPat, data) :
        result = re.findall(bodyPat, data)
        data = result[0]

    # now remove the java script
    p = re.compile(r'<script[^<>]*?>.*?</script>')
    data = p.sub('', data)

    # remove the css styles
    p = re.compile(r'<style[^<>]*?>.*?</style>')
    data = p.sub('', data)

    # remove html comments
    p = re.compile(r'')
    data = p.sub('', data)

    # remove all the tags
    p = re.compile(r'<[^<]*?>')
    data = p.sub('', data)

    return data

 
parser = argparse.ArgumentParser(description='Debug option')
parser.add_argument('-d', action='store_true', dest='debug', help='print debug info')
args = parser.parse_args()
debug = args.debug

inbox = mailbox.Maildir(maildir_path, factory=None)
db = MySQLdb.connect(host=db_host, port=db_port, user=db_user, passwd=db_pass, db=db_name, use_unicode=True,
                     charset="utf8")
db.set_character_set('utf8')
cur = db.cursor() 
cur.execute('SET NAMES utf8;')
cur.close()
db.commit()


def email_part_analyse(msg_part=None):

    if msg_part:
        # 3 части: plain, html, other text
        text_part = ["", "", ""]
    else:
        return ""

    for part in msg_part.get_payload():
        if debug:
            print "***** Анализ части сообщения *****"
        part_type = part.get_content_type()
        part_charset = part.get_param('charset')
        part_transfer_encode = part['Content-Transfer-Encoding']
        part_is_attach = part.has_key('Content-Disposition')
        part_filename = part.get_param("filename")
        skip_part = False

        if (part_charset == 'None') or part_is_attach:
            skip_part = True

        if debug:
            print 'Part is attach: %s' % part_is_attach
            print 'Part type: ', part_type
            print 'Part charset: ', part_charset
            print 'Part transf encode: ', part_transfer_encode
            print "Пропустить часть: %s" % skip_part
            print "Filename: %s " % part_filename

        if (part_type == "text/plain" or part_type == "text") and part_charset:
            # Как только нашли обычный текст, выводим с перекодировкой
            dirty_part = part.get_payload(decode=True)
            text_part[0] += unicode(dirty_part, str(part_charset), "ignore").encode('utf8', 'replace')
            if debug:
                print 'Text in plain: ', text_part[0], '\n'
        elif part_type == "text/html" and part_charset:
            # Если нашли текст в HTML, чистим от разметки и выводим с перекодировкой
            dirty_part = part.get_payload(decode=True)
            html = unicode(dirty_part, str(part_charset), "ignore").encode('utf8', 'replace')
            text_part[1] += remove_tags(html)
            if debug:
                print 'Text in HTML: ', text_part[1], '\n'
        elif part_type == "multipart/alternative" or part_type == "multipart/related":
            # часть сама является составной, ищем блоки и делаем анализ
            text_part_new = email_part_analyse(msg_part=part)
            text_part[0] = text_part[0] + text_part_new[0]
            text_part[1] = text_part[1] + text_part_new[1]
            text_part[2] = text_part[2] + text_part_new[2]
        else:
            # Если тип части не текст, пробуем раскодировать
            try:
                dirty_part = part.get_payload(decode=True)
                html = unicode(dirty_part, str(part_charset), "ignore").encode('utf8', 'replace')
            except Exception as e:
                if debug:
                    print "Ошибка раскодирования части. %s" % str(e)
                pass
            else:
                text_part[2] += remove_tags(html)

        """
        if not skip_part:
            if part_type == "text/plain" or part_type == "text":
                # Как только нашли обычный текст, выводим с перекодировкой
                dirty = part.get_payload(decode=True)
                text += unicode(dirty, str(part_charset), "ignore").encode('utf8', 'replace')
                if debug:
                    print 'Message in plain: ', text, '\n'
            elif part_type == "text/html":
                # Если нашли текст в HTML, чистим от разметки и выводим с перекодировкой
                dirty = part.get_payload(decode=True)
                html = unicode(dirty, str(part_charset), "ignore").encode('utf8', 'replace')
                text += remove_tags(html)
                if debug:
                    print 'Message in HTML: ', text, '\n'
            else:
                # Если тип части не известен, пробуем раскодировать
                try:
                    dirty = part.get_payload(decode=True)
                    html = unicode(dirty, str(part_charset), "ignore").encode('utf8', 'replace')
                except Exception as e:
                    print "Ошибка раскодирования части. %s" % str(e)
                    text += ""
                else:
                    text += remove_tags(html)

                if debug:
                    print 'Message in UNKNOWN format: ', text, '\n'

        else:
            #text = text + u'Часть содержит не текст.\n'
            #+ '\n'.join(part.values())
            if debug:
               print "Часть содержит не текст.\n"
        """
        if debug:
            print "***** Конец части сообщения *****"

    return text_part


for key in inbox.iterkeys():
    try:
        msg = inbox[key]
    except email.errors.MessageParseError:
        # The message is malformed. Just leave it.
        continue

    msg_id = ""
    subject = ""
    cc = ""
    to = ""
    from_ = ""
    date_hdr = ""
    text = ""
 
    if msg.get_subdir() == 'new':
        if debug:
            print '********** Next message **********\n'
            print 'Filename :',key
         
        msg_id = msg['message-id']
         
        subject = msg.get('Subject', 'No subject provided')
        subject = line_decoder(subject)
         
        date_raw = msg.get('Date')
        p = re.compile('[(]')
        if date_raw:
            date_hdr = p.split(date_raw,1)[0]
        else:
            date_hdr = ""

         
        text = ""

        # Проверяем параметры сообщения
        broken_msg = False
        # Если параметр не определен, ставим empty
        cc = msg.get('Cc')
        if not cc:
            cc = "empty"
        cc = line_decoder(cc)

        to = msg.get('To')
        if not to:
            to = "empty"
            broken_msg = True
        to = line_decoder(to)

        from_ = msg.get('From')
        if not from_:
            from_ = "empty"
            broken_msg = True
        from_ = line_decoder(from_)

        maintype = msg.get_content_maintype()
        main_charset = msg.get_content_charset()
         
        if debug:
            print "MID:", msg_id
            print "From: ", from_
            print "To: ", to
            print 'Main type: ', maintype
            print 'Main charset', main_charset
            print 'Subj: ',subject
            print 'Date: ',date_hdr
            print "\n"

        if maintype == 'multipart':
            # Если это мультипарт, ищем текстовую часть письма
            if debug:
                print "** Multipart message **"
                print msg.get_payload()
                print len(msg.get_payload())

            # Если это мультипарт, то передаем его на обработку
            text2 = email_part_analyse(msg_part=msg)
            print "= "*30
            for one in text2[:2]:
                print one
                print "- "*30

            text += text2[0]

        elif (maintype == "text/plain" or maintype == "text" or maintype == "text/html") and main_charset:
            print "** NOT Multipart message **"
            dirty = msg.get_payload(decode=True)
            text += unicode(dirty, str(main_charset), "ignore").encode('utf8', 'replace')
            print 'Message in plain: ', text, '\n'
        elif not main_charset or not maintype:
            if debug:
                print 'Не указан main_charset. Битое сообщение.'
            #Если не определены параметры в заголовках, считаем что это битое сообщение не декодируем
            text += msg.get_payload(decode=True)
            broken_msg = True
        else:
            # Все остальное
            if debug:
                print 'Все остальное. Сообщение без обработки.'
            text += msg.get_payload(decode=True)
            broken_msg = True

        
        #Заносим полученные данные о письме в БД
        msg_datetime = parse(date_hdr)
        cur = db.cursor() 
        cur.execute("""INSERT INTO email_raw_data (message_id,sender,recipient,cc_recipient,message_title,\
                                               message_text,orig_date,create_date,isbroken)\
                                               VALUES (%s,%s,%s,%s,%s,%s,%s,now(),%s);""",\
                                               (MySQLdb.escape_string(msg_id),
                                                MySQLdb.escape_string(from_),
                                                MySQLdb.escape_string(to),
                                                MySQLdb.escape_string(cc),
                                                MySQLdb.escape_string(subject),
                                                MySQLdb.escape_string(text),
                                                msg_datetime,
                                                int(broken_msg)))
         
        #print query,'\n'
        cur.close()
        db.commit() 
        
        #После обработки письма его необходимо пометить как прочитанное и поместитьв папку ~/Maildir/cur
        msg.set_subdir('cur')
        msg.add_flag('S')
        newkey = inbox.add(msg)
        inbox.remove(key)
        if debug:
            print 'Перенос в прочитанные...\n'
            print 'Битое: ', broken_msg
    else:
        if debug:
            #print 'Сообщение уже обработано...\n'
            pass

db.close()


