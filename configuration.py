#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""

db_host = "localhost"
db_user = "conparser"
db_pass = "Qazcde123"
db_port = 3306
db_name = "conparser"

# Каталог анализатора, из которого беруться сообщения для анализа
maildir_path = "/home/sergey/Maildir"

# Сслыка для работы системы обучения
main_link = "http://localhost:8585/api/message/"

# Параметры аккаунта откуда будут забираться сообщения для доставки в каталог.
smtp_email = "vipct@conparser.ru"
smtp_server = "smtp.yandex.ru"
smtp_pass = "Qazcde123"

# Кому будут направляться сообщения о классификации от имени аккаунта анализатора. см. выше.
to_address = "sergey@reshim.com"

STOP_WORDS = ["как", "или", "который", "которых", "тот", "около", "они", "для", "Для", "Это", "это", "При", "при",
             "Кроме", "того", "чем", "под", "них", "его", "лат", "Также", "также", "этой", "этого",
              "com", "вам", "Вам", "Вами", "вами", "Вас", "вас", "ваше", "Ваше", "Все", "все"]


