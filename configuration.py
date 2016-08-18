#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""

db_host = "localhost"
db_user = "conparser"
#db_user = "demo"
db_pass = "Qazcde123"
db_port = 3306
db_name = "vipct"
# db_name = "conparser_demo"

TABLE_ARGS = {'mysql_engine': 'InnoDB',
              'mysql_charset': 'utf8',
              'mysql_collate': 'utf8_general_ci'
              }

# Каталог анализатора, из которого беруться сообщения для анализа
maildir_path = "/home/sergey/Maildir"

# Сслыка для работы системы обучения
main_link = "http://localhost:8585/api/message/"

# Параметры аккаунта откуда будут забираться сообщения для доставки в каталог.
smtp_email = "vipct@conparser.ru"
smtp_server = "smtp.yandex.ru"
smtp_pass = "Qazcde123"

# Кому будут направляться сообщения о классификации от имени аккаунта анализатора. см. выше.
# Список получателей собирается автоматически из настроек уведомлений (class Watch)
# to_address = "sergey@reshim.com sergey_fomin@list.ru"
# to_address = "sergey@reshim.com"

# Список адресов для уведомлений, в случае сбоя при формировании списка из базы наблюдателей
FAIL_NOTIFY_LIST = ["sergey@reshim.com"]

# Отправлять уведомления только  для категорий указанных в WARNING_CATEGORY
SEND_ONLY_WARNING = True

# Для каких категорий отправлять уведомления
WARNING_CATEGORY = ["conflict"]

STOP_WORDS = ["как", "или", "который", "которых", "тот", "около", "они", "для", "Для", "Это", "это", "При", "при",
              "Кроме", "того", "чем", "под", "них", "его", "лат", "Также", "также", "этой", "этого",
              "com", "вам", "Вам", "Вами", "вами", "Вас", "вас", "ваше", "Ваше", "Все", "все",
              "добрый", "день", "спасибо", "здравствуйте", "добрый день", "утро", "коллеги"]

# Список адресов, сообщения отправленные С и НА них буду игнорироваться системой.
# EXCEPTION_EMAIL = u"root@rework.reshim.com|undisclosed-recipients" #  из базы

# Список доменов почта НА и С которых будет анализироваться системой.
# Список задается именами доменов разделенных "|" без пробелов
# Если надо проверять все, оставить пустым
CHECK_DOMAINS = "" #  из базы

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

CHANNEL_TYPE = {0: "email", 1: "phone"}

DIALOG_MEMBER_TYPE = {0: "employee", 1: "client"}

# Режим работы системы. True - рабочий режим (ведем статистику и шлем уведомления),
# False - режим обучения (не ведется статистика, не отправляются уведомления)
PRODUCTION_MODE = False


# Ключ доступа к API провайдера телефонии
PHONE_API_KEY = "59d9448ae3d1f9b44379cc29887dce89"

# Каталог временного хранения записей телефонных разговоров
PHONE_CALL_TEMP = "temp"

# Ключ указывает, будет ли система пытаться резать запись по паузам в разговоре и разпознавать по фразам.
# Короткие отрезки лучше распознаются.
PHONE_CALL_SPLIT_SILENCE = True

# слова и сочетания характерные для телефонных разговоров компании
# помогают улучшить результат транскрипции разговора
PHONE_CONTEXT_PHRASES = ["электронная подпись",
                         "стоимость", "налоговая", "расчетный", "счет",
                         "получим", "паспорт", "копия", "одна", "у нас",
                         "юрбюро", "компания", "очень приятно", "меня зовут", "чем могу помочь", "сколько стоит",
                         "адрес регистрации компании", "вы кстати", "выбрать и заказать печати",
                         "выбрать компанию", "бухгалтерское сопровождение", " съездить в фонд социального страхования",
                         "подать их в налоговую", "вам нужно", "подготовить документы на регистрацию",
                         "мы же упростили", "соответственно нам достаточно", "мы сами приедем к вам", "Для вас это займет",
                         "ездить никуда не нужно", "то есть", "если мы сегодня с вами начнем работать",
                         "отлично у нас есть услуга", "для вас", "мы можем помочь следующим образом",
                         "по телефону соберем информацию", "встретимся у нотариуса", "где вам это будет удобно",
                         "через дней", "привезем вам документы о регистрации и печать", "организуем встречу по расчетному счету",
                         "консультируем по всем вопросам про ООО", "записываем вас в налоговую на удобное время",
                         "отправить вопросы по почте", "у нас были клиенты", "у него", "в другом городе",
                         "Как называется организация"]

# При каком статусе звонка происходит его распознавание. Чтобы не распознавать занятое, нет ответа и т.д.
PHONE_CALL_STATUS_FOR_RECOGNIZE = "answered"

# При какой длительности звонка происходит его распознавание. Чтобы исключить ошибки набора, бросание трубки и т.д.
PHONE_CALL_DURATION_FOR_RECOGNIZE = 15
