# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 17:04:18 2015

@author: sergey
"""
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

import objects as CPO

sql = list()
sql.append("ALTER TABLE email_raw_data ADD COLUMN `message_text_html` MEDIUMTEXT NULL AFTER `message_text`;")
sql.append("ALTER TABLE `train_api` ADD COLUMN `train_epoch` INT(11) NULL AFTER `user_answer`;")
print "Перед выполнением закомменировать в objects.py CURRENT_TRAIN_EPOCH = read_epoch()."
sql.append("ALTER TABLE `train_data` ADD COLUMN `train_epoch` INT(11) NULL AFTER `category`;")
sql.append("ALTER TABLE `user_train_data` ADD COLUMN `train_epoch` INT(11) NULL AFTER `category`;")
sql.append("UPDATE `train_api` SET `train_epoch` = 0 WHERE `id` > 0;")
# Выполнить один раз
sql.append("UPDATE `train_data` SET `train_epoch` = 0 WHERE `id` > 0;")
# Выполнить один раз
sql.append("UPDATE `user_train_data` SET `train_epoch` = 0 WHERE `id` > 0;")


# Создаем новые таблицы
CPO.create_tables()

connection = CPO.Engine.connect()

# Обновляем базу
try:
    result = connection.execute(sql[0])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[1])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[2])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[3])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[4])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    if CPO.CURRENT_TRAIN_EPOCH == 0:
        result = connection.execute(sql[5])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    if CPO.CURRENT_TRAIN_EPOCH == 0:
        result = connection.execute(sql[6])
except Exception as e:
    print e.message, e.args
else:
    print result

connection.close()


