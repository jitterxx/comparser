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
to_address = "sergey@reshim.com sergey_fomin@list.ru"
#to_address = "sergey@reshim.com"

# Отправлять уведомления только  для категорий указанных в WARNING_CATEGORY
SEND_ONLY_WARNING = True

# Для каких категорий отправлять уведомления
WARNING_CATEGORY = ["conflict"]

STOP_WORDS = ["как", "или", "который", "которых", "тот", "около", "они", "для", "Для", "Это", "это", "При", "при",
             "Кроме", "того", "чем", "под", "них", "его", "лат", "Также", "также", "этой", "этого",
              "com", "вам", "Вам", "Вами", "вами", "Вас", "вас", "ваше", "Ваше", "Все", "все",
              "добрый", "день", "спасибо", "здравствуйте", "добрый день", "утро", "коллеги"]

# Список адресов, сообщения отправленные С и НА них буду игнорироваться системой.
EXCEPTION_EMAIL = u"root@rework.reshim.com|undisclosed-recipients"

# Список доменов почта НА и С которых будет анализироваться системой.
# Список задается именами доменов разделенных "|" без пробелов
# Если надо проверять все, оставить пустым
CHECK_DOMAINS = u"akrikhin.ru"

# Тип приложения которое будет прикреаляться к уведомлению и содержать пеерписку
# в которой учавствует подозрительное письмо
# Может быть pdf или html
FILE_ATTACH_TYPE = "pdf"

# Место положение скрипта для решения проблемы с отсутствием X сервера
WK_HTML_TO_PDF_PATH = "/usr/bin/wkhtmltopdf"

# Service receiver URL. Accept connection and data from email_eater and write MsgRaw to DB
receiver_url = "http://127.0.0.1:9595/post"

# Группы доступа для пользователей
# users -  обычные пользвоатели без привелегий
# admin - администраторы. Доступно управление пользователями и настройка системы уведомлений
ACCESS_GROUPS = {"users": "Пользователи", "admin": "Администраторы"}

USER_STATUS = ["Активен", "Отключен"]

TASK_STATUS = ["Новая", "В работе", "Закрыта"]

TASK_CLOSED_STATUS = 2

CLIENT_CHANNEL_TYPE = ["email"]



