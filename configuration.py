#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""

db_host = "localhost"
#db_user = "comparser"
#db_pass = "Qazcde123"
#db_port = 3306
db_user = "root"
db_pass = "OO00zZOK"
db_name = "classifier"
db_port = 33066
maildir_path = "/home/comparser/Maildir"

main_link = "http://conparser.reshim.com/api/message/"



aa = [(u'edible', 0.863784657224), (u'default', 0.0)]

for v,k in aa:
    print v
    print k