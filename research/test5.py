#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])
import re


isexception = False
debug = True
no_check = True
addresses = [u'vera@yurburo.ru', u'nbarchuk@rocketscienceacademy.org', u'yana@yurburo.ru', u'olga@yurburo.ru']

domain_search = re.compile(u'yurburo.ru', re.I|re.U)

for one in addresses:
    if domain_search.search(one):
        no_check = False
if no_check:
    isexception = True

if debug:
    print "Addressess: ", addresses
    print "Domains for check: ", re.split("|", u'yurburo.ru')
    print "Check result: ", not no_check
    print "EXCEPTION: ", isexception
