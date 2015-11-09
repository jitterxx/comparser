#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""
from operator import itemgetter
import re
import argparse
import mod_classifier as cl
import mysql.connector
import math
import datetime
from configuration import *
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


parser = argparse.ArgumentParser(description="Если -с не указано, происходит определение всех "
                                             "категории без проверки. \n"
                                             "Если -l не указано, обрабатываются первые 100 записей.")
parser.add_argument("-c",action="store",help="Проверяем сообщения на корректность определения категорий. "
                                             "Список категорий смотрите по -s",dest='category')
parser.add_argument("-l",action="store",help="Количество записей для обработки",dest='limit',type=int)
parser.add_argument("-db",action="store",help="Имя классификатора",dest='db')
parser.add_argument("-s",action="store_true",help="Показать классификаторы, категории, лимиты",dest='show')
parser.add_argument("-d",action="store_true",help="Показать отладку.",dest='debug')
args = parser.parse_args()




if not args.db == None:
    #Указана БД классификатора, работаем используя лимит
    #Создаем объект классификатора
    f_cl = cl.fisherclassifier(cl.specfeatures)

    #Подключаем данные обучения
    f_cl.setdb(args.db)
    f_cl.loaddb()

    #Настрока категорий
    cat = f_cl.category_code
    minimums = f_cl.minimums
    cat_count = {}
    
    
    #Настройка параметров работы
    if args.limit == None: 
        lim = (10,)
    else: 
        lim = (args.limit,)

    if args.show:
        #Показать настройки БД классификатора
        for i in cat.keys():
            print 'Категория: ',cat[i],'(',i,') : ',minimums[i]
        f_cl.unsetdb()

    if not args.show:
        #Открываем базу с реальными данными
        real_db = mysql.connector.connect(host=db_host, user=db_user, passwd=db_pass, database=db_name)
        con = real_db.cursor(buffered=True)
        con_update = real_db.cursor(buffered=True)

        #Получаем реальные данные
        query = ('SELECT * FROM email_cleared_data WHERE not isclassified LIMIT %s;')
        con.execute(query,lim)

        if con.fetchone():
            for real in con:
                row = dict(zip(con.column_names, real))
                if args.debug:
                    print '*'*100,'\n'
                    print row['id'],' ','.'*10
                    print('От: {}\nКому: {}\nТема: {}'.format(row['sender'],row['recipients'],row['message_title']))
                    print 'Текст: \n',row['message_text'],'\n'
                    
                answer = f_cl.classify_mr(row,default='0')
                answer.reverse()
                last = 3
                if len(answer) < 3: last = len(answer)

                answer_str = ''
                for a in range(last):
                    #запишем первые три варинта в стороку ответа
                    key = answer[a].keys()[0]
                    value = answer[a].values()[0]
                    answer_str = answer_str +':'+ key +'-'+ str(value)
                answer_str = answer_str[1:]    
                    
                if args.debug:
                    print 'Категория: ',answer_str,'\n'
                    print '*'*100,'\n'
                    raw_input("Press Enter to continue...")

                    #cat_count[answer] += 1

                #Устанавливаем/обновляем классификацию реальных данных
                query = ('UPDATE email_cleared_data SET isclassified=%s,category=%s WHERE id=%s;')
                data = (1, answer_str, row['id'])
                con_update.execute(query,data)
                real_db.commit()

                # Добавлем запись в таблицу train_api для работы API и функции переобучения
                query = ('INSERT INTO train_api (message_id, category, date, user_action, user_answer) VALUES '
                         '(%s, %s, %s, %s, %s);')
                data = (row["message_id"], answer_str, datetime.datetime.now(), 0, "")
                con_update.execute(query, data)
                real_db.commit()


        else:
            if args.debug: print 'Новых сообщений нет.'

        con.close()
        con_update.close()
        real_db.close()
        f_cl.unsetdb()
    
    if args.category:
        print 'Проверяем определение категорий.'

else:
    print 'Выбраны неверные опции или невыбраны вообще.'







