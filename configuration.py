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
maildir_path = "/home/vipct/Maildir"

# Сслыка для работы системы обучения
main_link = "http://localhost:8585/api/message/"

# Настройки для аккаунта на которые приходят сообщения для помещения в каталог анализатора
from_email = "edible@conparser.ru"
smtp_server = "smtp.yandex.ru"
smtp_pass = "Cthutq123"

# Адрес на который будут приходить уведовления после анализа. Если None, уведомления приходят отправителю сообщения
to_email = None


