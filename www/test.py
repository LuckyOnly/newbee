# coding:utf-8

i = {'password': u'c8837b23ff8aaa8a2dde915473ce0991', 'name': u'2', 'email': u'1047670763@qq.com'}
print i
name = i['name'].strip()
email = i['email'].strip().lower()
password = i['password']
print name,email,password
import re
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')
print _RE_MD5.match(password)