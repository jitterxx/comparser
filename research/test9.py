#!/usr/bin/python -t
# coding: utf8

"""
1. Читаем результаты классификации из базы
2. Если классификация попадает в условия, то формируем уведомление
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import logging
from objects import *
from sqlalchemy import and_, func

s = u'абвгджзиелмн'

print s
print s.decode('utf-8')
print s


f = file('text.txt', 'w')
f.write(s)
f.close()


