#!/usr/bin/python -t
# coding: utf8
"""
Классификация текстов(документов), сообщений и т.д.

1. Содержит модели классификаторов
2. Для каждой модели определены методы загрузки данных из базы, тренировки и извлечения признаков

"""
from bs4 import BeautifulSoup
import re
import mysql.connector
import math
import decimal
from configuration import *
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


class classifier:
    """
        Исходный класс
    """

    def __init__(self, getfeatures, filename=None):
        # Счетчики комбинаций признак/категория
        #self.fc={}
        # Счетчики документов в каждой категории
        #self.cc={}
        self.getfeatures=getfeatures
        self.thresholds={}
        #Храним тут Сколько раз признак появлялся в данной категории для fcount
        self.fc = {}
        #Храним сколько образцов отнесено к данной категории для catcount
        self.cc = {}

    #Добавьте два простых метода для установки и получения значений,
    #причем по умолчанию пусть возвращается значение 1,0
    def setthreshold(self,cat,t):
        self.thresholds[cat]=t
    
    def getthreshold(self,cat):
        if cat not in self.thresholds: return 1.0
        return self.thresholds[cat]

    # Увеличить счетчик пар признак/категория
    def incf(self,f,cat):
        #self.fc.setdefault(f,{})
        #self.fc[f].setdefault(cat,0)

        count=self.fcount(f, cat)
        if count == 0:
            query = ('insert into fc (feature,category,count) values (%s,%s,1);')
            self.con.execute(query,(f,cat))
            self.db.commit()
            self.fc[f] = {cat: 1}
        else:
            query = ('update fc set count=%s where feature=%s and category=%s;')
            self.con.execute(query,(count+1,f,cat))
            self.db.commit()
            self.fc[f][cat] += 1
        #print 'incf :',f,cat,count,'\n'
    
    # Увеличить счетчик применений категории
    def incc(self,cat):

        count = self.catcount(cat)
        print 'incc :', cat, count,'\n'

        if count == 0:
            query = ('insert into cc (category,count) values (%s,1);')
            self.con.execute(query,(cat,))
            self.cc[cat] = 1
        else:
            query = ('update cc set count=%s where category=%s;')
            self.con.execute(query,(count+1,cat))
            self.cc[cat] += 1
        self.db.commit()


    # Сколько раз признак появлялся в данной категории
    def fcount(self,f,cat):
        #query = ('select count from fc where feature=%s and category=%s;')
        #self.con.execute(query,(f,cat))
        #res = self.con.fetchone()
        #if res is None: return 0
        #else: 
        #    return float(res[0])
        if f in self.fc and cat in self.fc[f]:
            return float(self.fc[f][cat])
        return 0.0

    # Сколько образцов отнесено к данной категории
    def catcount(self,cat):
        #query = ('select count from cc where category=%s;')
        #self.con.execute(query,(cat,))
        #res = self.con.fetchone()
        #if res is None: return 0
        #else: 
        #    return float(res[0])
        if cat in self.cc:
            return float(self.cc[cat])
        return 0
    
    # Общее число образцов
    def totalcount(self):
        #query = ('select sum(count) from cc;')
        #self.con.execute(query)
        #res = self.con.fetchone()
        #if res is None: return 0
        #return res[0]
        return sum(self.cc.values())
    
    # Список всех категорий
    def categories(self):
        #query = ('select category from cc;')
        #self.con.execute(query)
        #return [d[0] for d in self.con]
        return self.cc.keys()
    
    
    def fprob(self,f,cat):
        if self.catcount(cat)==0: return 0
        # Общее число раз, когда данный признак появлялся в этой категории,
        # делим на количество образцов в той же категории
        return self.fcount(f,cat)/self.catcount(cat)
        
    def weightedprob(self,f,cat,prf,weight=1.0,ap=0.5):
        # Вычислить текущую вероятность
        basicprob=prf(f,cat)
        # Сколько раз этот признак встречался во всех категориях
        totals=sum([self.fcount(f,c) for c in self.categories()])
        # Вычислить средневзвешенное значение
        bp=((weight*ap)+(totals*basicprob))/(weight+totals)
        return bp
    
    def classify(self,item,default=None):
        probs={}
        # Найти категорию с максимальной вероятностью
        max=0.0
        for cat in self.categories():
            probs[cat]=self.prob(item,cat)
            if probs[cat]>max:
                max=probs[cat]
                best=cat
        # Убедиться, что найденная вероятность больше чем threshold*следующая по величине
        for cat in probs:
            if cat==best: continue
            if probs[cat]*self.getthreshold(best)>probs[best]: return default
        return best

""" Метод Фишера """
class fisherclassifier(classifier):
    
    def __init__(self,getfeatures):
        classifier.__init__(self,getfeatures)
        self.minimums = {}
        self.specwords = {}
        self.category_code = {}
    
    def setminimum(self,cat,min): #Должен быть заменен на загрузку данных из БД
        self.minimums[cat]=min
    
    def getminimum(self,cat):
        if cat not in self.minimums: return 0
        return self.minimums[cat]
    
    #Метод train принимает образец (в данном случае документ) и классификацию
    def train(self,item,cat):
        features=self.getfeatures(item,self.specwords)
        # print "Category: %s" % cat
        # print "Features: %s" % features
        
        # Увеличить счетчики для каждого признака в данной классификации
        for f in features:
            #print "Word: %s" % f
            self.incf(f, cat)
        
        # Увеличить счетчик применений этой классификации
        self.incc(cat)

    def classify(self,item,default=None):
        # Цикл для поиска наилучшего результата
        best=default
        max=0.0
        for c in self.categories():
            p=self.fisherprob(item,c)
            # Проверяем, что значение больше минимума
            if p>self.getminimum(c) and p>max:
                best=c
                max=p
        return best

    def classify_mr(self,item,default=None):
        #Функция классификации возвращает набор из всех результатов (category, probability)
        #отсортированных по убыванию
        #Цикл для поиска наилучшего результата
        best_mr = [{'default': 0}]
        best=default
        max=0.0
        for c in self.categories():
            p=self.fisherprob(item,c)
            # Проверяем, что значение больше минимума
            if p>self.getminimum(c) and p>max:
                best=c
                max=p
                best_mr.append({c:p})

        return best_mr

        
    def cprob(self,f,cat):
        # Частота появления данного признака в данной категории
        clf=self.fprob(f,cat)
        if clf==0: return 0
        # Частота появления данного признака во всех категориях
        freqsum=sum([self.fprob(f,c) for c in self.categories( )])
        # Вероятность равна частоте появления в данной категории, поделенной на
        # частоту появления во всех категориях
        p=clf/(freqsum)
        return p
   
    """def fisherprob_old(self,item,cat):
        # Переменожить все вероятности
        p=decimal.Decimal(1)
        features=self.getfeatures(item)
        for f in features:
            p*=(self.weightedprob(f,cat,self.cprob))
        # Взять натуральный логарифм и умножить на -2
        #fscore=-2*math.log(p)
        fscore=-2*p.ln()
        # Для получения вероятности пользуемся обратной функцией хи-квадрат
        return self.invchi2(fscore,len(features)*2) """

    def fisherprob(self,item,cat):
        # Переменожить все вероятности
        p=decimal.Decimal(1) #Используем Децимал для нужной точности
        features=self.getfeatures(item,self.specwords)
        for f in features:
            wp = self.weightedprob(f,cat,self.cprob)
            p*=decimal.Decimal(wp)
        # Взять натуральный логарифм и умножить на -2
        fscore=-2*p.ln()
        # Для получения вероятности пользуемся обратной функцией хи-квадрат
        p2 = float(fscore)
        return self.invchi2(p2,len(features)*2)

    def invchi2(self,chi,df):
        m = chi / 2.0
        sum = term = math.exp(-m)
        for i in range(1, df//2):
            term *= m / i
            sum += term
        return min(sum, 1.0)

    # Подключаем БД классификатора. DB = имя_схемы в Mysql
    def setdb(self,db):
        self.db = mysql.connector.connect(host=db_host, port=db_port, user=db_user, passwd=db_pass, database=db)
        self.con = self.db.cursor(buffered=True)

        """
        
        query = ('CREATE TABLE IF NOT EXISTS cc ('
        'id int(11) NOT NULL AUTO_INCREMENT,'
        'category varchar(255) DEFAULT NULL,'
        'count int(11) DEFAULT NULL, '
        'PRIMARY KEY (id)) ENGINE=InnoDB DEFAULT CHARSET=utf8;')
        
        self.con.execute(query)
        self.db.commit()
        
        query = ('CREATE TABLE IF NOT EXISTS fc ('
                 'id int(11) NOT NULL AUTO_INCREMENT, '
                 'feature varchar(255) DEFAULT NULL, '
                 'category varchar(255) DEFAULT NULL, '
                 'count int(11) DEFAULT NULL, '
                 'PRIMARY KEY (id) '
                 ') ENGINE=InnoDB DEFAULT CHARSET=utf8;')
        self.con.execute(query)
        self.db.commit()

        query = ('CREATE TABLE IF NOT EXISTS specwords ('
                 'id int(11) NOT NULL AUTO_INCREMENT, '
                 'code varchar(255) DEFAULT NULL, '
                 'word varchar(255) DEFAULT NULL, '
                 'PRIMARY KEY (id) '
                 ') ENGINE=InnoDB DEFAULT CHARSET=utf8;')
        self.con.execute(query)
        self.db.commit()
        
        query = ('CREATE TABLE IF NOT EXISTS category ('
                 'id int(11) NOT NULL AUTO_INCREMENT,'
                 'code varchar(45) NOT NULL,'
                 'category varchar(255) NOT NULL,'
                 'minimum float NOT NULL DEFAULT "0",'
                 'PRIMARY KEY (id), UNIQUE KEY code_UNIQUE (code)'
                 ') ENGINE=InnoDB DEFAULT CHARSET=utf8;')
        self.con.execute(query)
        self.db.commit()
        
        #Создание таблицы для тренировочных данных
        query = ('CREATE TABLE IF NOT EXISTS train_data ('
                'id int(11) NOT NULL AUTO_INCREMENT,'
                'message_id varchar(255) DEFAULT NULL,'
                'sender varchar(255) DEFAULT NULL,'
                'sender_name varchar(255) DEFAULT NULL,'
                'recipients text,'
                'recipients_name text,'
                'cc_recipients text,'
                'cc_recipients_name text,'
                'message_title text,'
                'message_text mediumtext,'
                'orig_date datetime DEFAULT NULL,'
                'сreate_date datetime DEFAULT NULL,'
                'category varchar(255) DEFAULT NULL,'
                'PRIMARY KEY (id)'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8;')
        self.con.execute(query)
        self.db.commit()
        """
        
        #Закрываем курсор, базу оставляем открытой для созданного класса
        #self.con.close()

    def load_specwords(self):
        #Загружаем  спецпризнаки
        con = self.db.cursor(buffered=True)
        query = ('SELECT * FROM specwords;')
        con.execute(query)
        for line in con:
            row = dict(zip(con.column_names, line))
            self.specwords[row['code']] = row['word']
        
        con.close()

    # загрузка данных классификатора из базы
    def loaddb(self):
        
        # загружаем категории, минимумы
        con = self.db.cursor(buffered=True)
        query = ('SELECT code, minimum, category FROM category;')
        con.execute(query)
        for d in con:
            self.setminimum(d[0],d[1])
            self.category_code[d[0]] = d[2]
        
        # Загружаем  спецпризнаки
        self.load_specwords()
        
        # Загружаем cколько раз признак появлялся в данной категории для fcount
        query = ('select feature, category, count from fc group by feature, category;')
        self.con.execute(query)
        for f in self.con:
            
            self.fc.setdefault(f[0],{})
            self.fc[f[0]].setdefault(f[1],0)
            self.fc[f[0]][f[1]] = f[2]
        
       
        # загружаем сколько образцов отнесено к данной категории для catcount
        query = ('select category,count from cc;')
        self.con.execute(query)
        for d in self.con:
            self.cc[d[0]] = d[1]
        
        con.close()
    
    #отключаем базу классификатора
    def unsetdb(self):
        self.db.close()

    #Функция тренировки классификатора
    def sql_train(self):

        con = self.db.cursor(buffered=True)
        query = ('SELECT * FROM train_data;')
        con.execute(query)

        for train_row in con:
            #Формируем словарь всей записи для entry
            row = dict(zip(con.column_names, train_row))
            print 'Train row: \n',row['sender'],'|',row['recipients'],'|',row['message_title'],'|', \
                  row['message_text'],'|',row['orig_date'],'|',row['category']
            
            #Формируем словарь для entry
            entry=row
            
            #Готовим словарь признаков для обучения
            #features = entryfeatures(entry)
            cat = row['category']
            self.train(entry,cat)
            
            #Увеличить счетчики для каждого признака в данной классификации
            #for f in features:
            #    cl.incf(f,cat)
            # Увеличить счетчик применений этой классификации
            #cl.incc(cat)

        con.close()

    # Функция тренировки классификатора на данных пользовательского контроля
    def user_train(self):

        con = self.db.cursor(buffered=True)
        query = ("SELECT * FROM user_train_data where create_date >= '2016-03-11 11:55:00';")
        con.execute(query)

        for train_row in con:
            # Формируем словарь всей записи для entry
            row = dict(zip(con.column_names, train_row))
            # print 'Train row: \n',row['sender'],'|',row['recipients'],'|',row['message_title'],'|', \
            #      row['message_text'],'|',row['orig_date'],'|',row['category']

            # Формируем словарь для entry
            entry=row

            # Готовим словарь признаков для обучения
            # features = entryfeatures(entry)
            cat = row['category']
            self.train(entry,cat)

            # Увеличить счетчики для каждого признака в данной классификации
            # for f in features:
            #     cl.incf(f,cat)
            #  Увеличить счетчик применений этой классификации
            # cl.incc(cat)

        con.close()

        
""" Функция извлечения признаков """
def specfeatures(entry, specwords):
    """ Функция для получения признаков(features) из текста
    Выделяет следующие признаки:
    1. email отправителя
    2. email получателей
    3. Слова из темы сообщения
    4. Все пары слов из темы сообщения
    5. Определенные сочетания из темы сообщения
    6. Слова из текста
    7. Все пары слов из текста
    8. Определенные пары слов из текста (specwords)
    9. Оригинальное время создания сообщения, только HH:MM\

    """    
    #print 'Text: \n', entry['message_text']
    splitter=re.compile('\\W*',re.UNICODE)
    splitter1=re.compile(',',re.UNICODE)
    f={}
    # Извлечь и аннотировать слова из заголовка
    titlewords=[s.lower( ) for s in splitter.split(entry['message_title']) 
                if len(s)>2 and len(s)<20]
    for w in titlewords: 
        #print 'Title: ',w,'\n'
        f['Title:'+w]=1
    
    # Извлечь и аннотировать слова из recipients
    """
    recipients=[s.lower( ) for s in splitter1.split(entry['recipients']) 
                if len(s)>2 and len(s)<20]
    for w in recipients: 
        #print 'Recipit: ',w,'\n'
        f['Recipients:'+w]=1
    
    # Извлечь и аннотировать слова из recipients_name
    recipients_name=[s.lower( ) for s in splitter1.split(entry['recipients_name']) 
                    if len(s)>2 and len(s)<20]
    for w in recipients_name: 
        #print 'Recipit name: ',w,'\n'
        f['Recipients_name:'+w]=1                
    """

    # Извлечь слова из резюме
    summarywords=[s for s in splitter.split(entry['message_text'])
                  if len(s)>2 and len(s)<20 and s not in STOP_WORDS]
    #print 'sum words: ',summarywords

    # Подсчитать количество слов, написанных заглавными буквами
    uc=0
    for i in range(len(summarywords)):
        w=summarywords[i]
        f[w]=1
        if w.isupper(): uc+=1
        # Выделить в качестве признаков пары слов из резюме
        if i<len(summarywords)-1:
            j = i+1
            l = [summarywords[i],summarywords[j]]
            twowords = ' '.join(l)
            #print 'Two words: ',twowords,'\n'
            f[twowords]=1
            
    # Оставить информацию об авторе без изменения
    """
    f['Sender:'+entry['sender']]=1
    f['Sender_name:'+entry['sender_name']]=1
    """
    
    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(summarywords)) and (float(uc)/len(summarywords)>0.3): f['UPPERCASE']=1
    
    #Извлекаем спец слова
    str = re.compile(r'[,.!?*"\']*',re.U|re.I)
    text = str.sub('',entry['message_text'])
    #print text,'\n'
    for key in specwords.keys():
        match = re.search(specwords[key],text,re.U|re.I)
        if match: 
            #print key,specwords[key],'\n'
            str = key+':'+specwords[key]
            f[str] = 1

    return f

"""
STOP_WORDS = ["как", "или", "который", "которых", "тот", "около", "они", "для", "Для", "Это", "это", "При", "при",
             "Кроме", "того", "чем", "под", "них", "его", "лат", "Также", "также", "этой", "этого"]
"""
