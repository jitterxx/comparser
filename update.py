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

connection = CPO.Engine.connect()

try:
    result = connection.execute(sql[0])
except Exception as e:
    print e.message, e.args
else:
    print result

connection.close()


