#!/usr/bin/python -t
# coding: utf8

"""
Импорт данных в тренировочную базу из xls

"""
import xlrd
import re
import argparse
import mysql.connector
import math
from configuration import *
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


def xls_import(db,xls_file):
    #Открываем файл
    rb = xlrd.open_workbook(xls_file,formatting_info=True)
    sheet = rb.sheet_by_index(0)

    #Открываем базу с тренировочными данными
    train_db = mysql.connector.connect(host=db_host, user="root", passwd="OO00zZOK", port="33066", database=db)
    con = train_db.cursor(buffered=True)

    for rownum in range(sheet.nrows):
        row = sheet.row_values(rownum)
        print len(row)
        
        query = ('INSERT INTO train_data (message_id,sender,sender_name,recipients,recipients_name,'
                 'cc_recipients,cc_recipients_name,message_title,message_text,'
                 'orig_date, create_date, category) VALUES'
                 '("tt",%s,%s,%s,%s,%s,%s,%s,%s,now(),now(),%s);')
        data = (row[0],'',row[1],'','','',row[2],row[3],row[4])
        con.execute(query,data)
        train_db.commit()

    con.close()
    train_db.close()
    

parser = argparse.ArgumentParser(description="Если ничего не указано, ничего не делаем.")
parser.add_argument("-f", action="store", help="Имя файла для импорта", dest='xfile')

args = parser.parse_args()

xls_import(db_name, args.xfile)


