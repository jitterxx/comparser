# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 17:04:18 2015

@author: sergey
"""
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

import objects as CPO
import configuration
import datetime


# Анономизатор для демо версии
# заменяет поля ОТ, КОМУ, КОПИЯ
# заменяет текст поля Тема и сообщение на художественный текст

