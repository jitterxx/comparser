#!/usr/bin/python -t
# coding: utf8

"""

Основной скрипт фильтрации содержимого и очистки

"""
import argparse
from email.utils import parseaddr
import mysql.connector
import re
import html2text
from configuration import *
import datetime
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


def remove_spec(text):
    text = re.sub(r'[\s]+',' ',text,re.U|re.I)
    text = re.sub(r'\\','',text,re.U|re.I)
    #data = "".join(re.findall(r'[\w\s\-@\.]',text,re.U|re.I))
    data = text
    return data


def remove_spec2(text):
    #data = re.sub(r'\\','',text,re.U|re.I)
    data = text
    #print type(data), type(text)
    #print 'Raw text: \n',text

    # remove the newlines
    data = data.replace("\\n", " ")
    data = data.replace("\\r", " ")
       
    # replace consecutive spaces into a single one
    data = " ".join(data.split())
    
    return data

    
def remove_html_tags(html):
    data = html2text.html2text(html)
    
    return data


#Очищаем поля От, кому, копия. Отделяем адреса от ФИО
def get_emails(entry,data):
    #get list of from entry separated by ','
    from_list = re.split(',',entry['sender'],re.U|re.I)
    #print entry['sender']
    to_list = re.split(',',entry['recipient'],re.U|re.I)
    #print entry['recipient']
    cc_list = re.split(',',entry['cc_recipient'],re.U|re.I)
    #print entry['cc_recipient']
    
    for item in from_list:
        str = parseaddr(remove_spec(item))
        if data['sender']: data['sender'] = data['sender']+','+str[1]
        else: data['sender'] = str[1]
        if data['sender_name']: data['sender_name'] = data['sender_name']+','+str[0]
        else: data['sender_name'] = str[0]
        
        #check
        #print str
        #print data['sender']
        #print data['sender_name']

    for item in to_list:
        str = parseaddr(remove_spec(item))
        if data['recipients']: data['recipients'] = data['recipients']+','+str[1]
        else: data['recipients'] = str[1]
        if data['recipients_name']: data['recipients_name'] = data['recipients_name']+','+str[0]
        else: data['recipients_name'] = str[0]
        
        #check
        #print str
        #print data['recipients']
        #print data['recipients_name']

    for item in cc_list:
        str = parseaddr(remove_spec(item))
        if data['cc']: data['cc'] = data['cc']+','+str[1]
        else: data['cc'] = str[1]
        if data['cc_name']: data['cc_name'] = data['cc_name']+','+str[0]
        else: data['cc_name'] = str[0]
        
        #check
        #print str
        #print data['cc']
        #print data['cc_name']
        
    return data


#Очищаем поле тема
def get_title(entry,data):
    text = remove_spec2(entry['message_title'])
    text = remove_html_tags(text)
    data['message_title'] = text
    return data


#Выделяем из текста первый блок, отсекам прошлые сообщения, пересылки и т.д.
def get_main_text(text):
    """str = from:|от:|написал:|wrote:|от:|
              [-]{4,8}\s?[\w\s]{10,30}\s?[-]{4,8}|
              \-{4,8}\s?исходное сообщение\s?\-{4,8}|
              \-{4,8}\s?пересылаемое сообщение\s?\-{4,8}|
              \-{4,8}\s?пересланное сообщение\s?\-{4,8}]"""
                    
    str = u'from:|от:|написал:|wrote:|от:|> >|>>|\-{4,8}\s?[\w\s]{10,30}\s?\-{4,8}'

    data = text
    p = re.compile(str,re.U|re.I)
    p1 = p.search(data)
    
    #print 'Raw: \n', text
    #print 'Вхождение: ',p1
    
    #Повторяем пока результат поиск не будет отрицательным
    while p1:
        text2 = p.split(data,1)
        data = text2[0]
        #print 'Splitted: \n',data
        p1 = p.search(data)        
        #print 'Вхождение: ',p1    
    return data


#Очистка темы и текста от спец символов и т.д.
def get_clear_text(entry,data):
    text = entry['message_text']
    text = remove_html_tags(text)
    text = remove_spec2(text)    
    data['message_text'] = text

    return data


#отсеиваем ненужные сообщения (каледарные, нотификации, исключения пользователей и т.д.)
def exception(entry,data):
    emails = u'root@rework.reshim.com|undisclosed-recipients'

    title_start = u"""Принять:|Прочтено:|Принято:|Read-Receipt:|Отменено:|Предложено новое время:"""
    text_start = u"""Тема:|Следующее собрание изменилось:|Запрос на новую встречу:|
                     Это собрание переслано:|Предложено новое время:|
                     Изменилась одна копия следующего собрания:"""

    #Тема начинается на
    title = re.compile(title_start,re.I|re.U)
    title_re = title.search(data['message_title'])
    if title_re: 
        #print data['message_title']
        #print title_re.group(0)
        data['isexception'] = 1

    #Текст начинается на
    text = re.compile(text_start,re.I|re.U)
    text_re = text.match(data['message_text'])
    if text_re: 
        #print data['message_title']
        #print text_re.group(0)
        data['isexception'] = 1
    
    #Адрес отправителя содержит
    #Адрес получателя содержит
    str = data['sender'] + ':' + data['recipients'] + ':' + data['cc']
    email = re.compile(emails,re.I|re.U)
    email_re = email.search(str)
    if email_re: 
        #print str
        #print email_re.group(0)
        data['isexception'] = 1
    
    return data

    
def broken(data):
    #check for empty sender, recipient fields
    if (data['sender'] == '') or (data['recipients'] == ''): 
        data['isbroken'] = 1
        
    #check if message have only attachment
    return data
    
parser = argparse.ArgumentParser(description="")
parser.add_argument("-d",action="store_true",help="Вывод отладочных данных",dest='debug')
parser.add_argument("-l",action="store",type=int,help="Обработка указанного количества записей, иначе"
                                                      "обрабатывается по 100 за один раз",dest='limit')
args = parser.parse_args()

if not args.debug: debug = False
else: debug = args.debug

if not args.limit: limit = 100
else: limit = args.limit

#Открываем грязную базу
dirty_db = mysql.connector.connect(host=db_host, port=db_port, user=db_user, passwd=db_pass, database="Raw_data")
dirty_con = dirty_db.cursor(buffered=True)

#Открываем чистую базу и базу ошибок
clear_db = mysql.connector.connect(host=db_host, port=db_port, user=db_user, passwd=db_pass, database="clear_data")
clear_con = clear_db.cursor(buffered=True)
err_con = clear_db.cursor(buffered=True)

#Получаем грязные данные
query = ('SELECT * FROM email_raw_data WHERE (NOT iscleared) and (sender like %s) LIMIT %s;')
dirty_con.execute(query,('%%',limit))

#Запоминаем обработанные номера записей
processed = [0]

for data in dirty_con:
    row = dict(zip(dirty_con.column_names, data))

    clear_data = {'message_id':'','sender':'','sender_name':'','recipients':'',
                  'recipients_name':'','cc':'','cc_name':'','message_title':'',
                  'message_text':'','orig_date':'','create_date':'','isbroken':0,'isexception':0}
    #set unchanged fields
    clear_data['message_id'] = row['message_id']
    clear_data['orig_date'] = row['orig_date']
    clear_data['create_date'] = row['create_date']
    clear_data['isbroken'] = row['isbroken']
    
    clear_data = get_emails(row,clear_data)
    clear_data = get_title(row,clear_data)
    clear_data = get_clear_text(row,clear_data)
    clear_data['message_text'] = get_main_text(clear_data['message_text'])
    clear_data = exception(row,clear_data)
    clear_data = broken(clear_data)
    
    if debug:
        print '*'*100,'\n'
        print row['id'],' ','.'*10
        print('От: {}\nАдрес: {}\n'.format(clear_data['sender_name'],clear_data['sender']))
        print('Кому: {}\nАдреса: {}\n'.format(clear_data['recipients_name'],clear_data['recipients']))
        print 'Тема: ',clear_data['message_title']
        print 'Текст:\n',clear_data['message_text']
        print 'Битое: ',clear_data['isbroken']
        print 'Исключение: ',clear_data['isexception']
        print '*'*100,'\n'

    #Remember processed entry id
    processed.append(int(row['id']))
    
    #Insert clear message in Clear DBs
    data = (clear_data['message_id'],clear_data['sender'],clear_data['sender_name'],
            clear_data['recipients'],clear_data['recipients_name'],clear_data['cc'],
            clear_data['cc_name'],clear_data['message_title'],clear_data['message_text'],
            clear_data['orig_date'],clear_data['create_date'])

    if not (clear_data['isbroken']) and not(clear_data['isexception']):
        #pass to analyse db
        ins_query = ('INSERT INTO email_cleared_data (message_id,sender,sender_name,recipients,'
                 'recipients_name,cc_recipients,cc_recipients_name,message_title,message_text,'
                 'orig_date,create_date) VALUES'
                 '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);')

        clear_con.execute(ins_query,data)
        clear_db.commit()
        if debug:
            print 'Data inserted to ClearDB.'
            print 'ID: ',clear_con.lastrowid

        
    else:
        #message have error, to err db
        ins_query = ('INSERT INTO email_err_cleared_data (message_id,sender,sender_name,recipients,'
                 'recipients_name,cc_recipients,cc_recipients_name,message_title,message_text,'
                 'orig_date,create_date) VALUES'
                 '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);')

        err_con.execute(ins_query,data)
        clear_db.commit()

        if debug:
            print 'Data inserted to ClearErrorDB.'
            print 'ID: ',err_con.lastrowid
    
if debug:
    print processed

#Mark dirty message as isCleared
dirty_con.close()
dirty_con = dirty_db.cursor(buffered=True)
up_query = ('UPDATE email_raw_data SET iscleared = 1 WHERE id = %s;')

for id in processed:
    dirty_con.execute(up_query,(id,))
    dirty_db.commit()

if debug:
    print 'Dirty data updated.'
    
    
dirty_con.close()
clear_con.close()
err_con.close()
dirty_db.close()
clear_db.close()
