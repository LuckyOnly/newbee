# coding:utf-8

from transwarp.web import get, view
from models import User, Blog, Comment

# @view('test_users.html')
@get('/')
def test_users():
    users = User.find_first('where admin = ?',0)
    # return dict(users=users)
    return '<h1>hello</h1>'

@view('test_users.html')
@get('/')
def test_users():
    users = User.find_first('where admin = ?',0)
    # print users.name
    return dict(users=users)
    # return '<h1>hello</h1>'