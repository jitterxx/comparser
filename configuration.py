#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""

db_host = "localhost"
db_user = "vipct"
db_pass = "Qazcde123"
db_port = 3306
db_name = "vipct"

# Каталог отккда забираются сообщения для анализа после доставки.
maildir_path = "/home/vipct/Maildir"

# Ссылка для работы с обучением системы
main_link = "http://vipct.conparser.ru/api/message/"

# Параметры аккаунта откуда будут забираться сообщения для доставки в каталог.
smtp_email = "vipct@conparser.ru"
smtp_server = "smtp.yandex.ru"
smtp_pass = "Qazcde123"

# Кому будут направляться сообщения о классификации от имени аккаунта анализатора. см. выше.
to_address = "v.vlasova@vipct.ru"
SEND_ONLY_WARNING = True

STOP_WORDS = ["как", "или", "который", "которых", "тот", "около", "они", "для", "Для", "Это", "это", "При", "при",
             "Кроме", "того", "чем", "под", "них", "его", "лат", "Также", "также", "этой", "этого",
              "com", "вам", "Вам", "Вами", "вами", "Вас", "вас", "ваше", "Ваше", "Все", "все",
              "добрый", "день", "спасибо", "здравствуйте", "добрый день", "утро", "коллеги"]

# Список адресов, сообщения отправленные С и НА них буду игнорироваться системой.
EXCEPTION_EMAIL = u"root@rework.reshim.com|undisclosed-recipients|hr@vipservice.ru|dobro@vipservice.ru|" \
                  u"dl-avia@vipct.ru|iway@iwayex.com|noreply@uralairlines.ru"

