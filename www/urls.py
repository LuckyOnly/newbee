# coding:utf-8

from transwarp.web import get, view,ctx,post
from models import User, Blog, Comment
from apis import api,Page


def _get_page_index():
    page_index = 1
    try:
        print ctx.request.get('page','1')
        page_index = int(ctx.request.get('page','1'))
    except ValueError:
        pass
    return page_index

# @view('test_users.html')
@get('/demo')
def test_users():
    users = User.find_first('where admin = ?',0)
    # return dict(users=users)
    return '<h1>hello</h1>'

@view('test_users.html')
@get('/test')
def test_users():
    users = User.find_first('where admin = ?',0)
    # print users.name
    return dict(users=users)
    # return '<h1>hello</h1>'




def _get_blogs_by_page():
    total = Blog.count_all()
    page = Page(total, _get_page_index())
    blogs = Blog.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return blogs, page

@view('blogs.html')
@get('/123')
def index():
    blogs, page = _get_blogs_by_page()
    return dict(page=page, blogs=blogs, user=ctx.request.user)

@view('blogs1.html')
@get('/blogs1')
def index():
    blogs = Blog.find_all("where 1=1")
    total = Blog.count_all()
    page = Page(total)
    # 查找登陆用户:
    user = User.find_first('where email=?', 'admin@example.com')
    return dict(blogs=blogs, user=user,page=page)

@api
@get('/api/user')
def api_get_users():
    total = User.count_all()
    # page = Page(total,_get_page_index())
    page = Page(total)
    users = User.find_by('order by created_at desc limit ?,?',page.offset,page.limit)
    for u in users:
        u.password = "****"
    return dict(users=users,page=page)


import re,hashlib
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')
_RE_EMAIL = re.compile(r'[0-9a-z\.\-\_]+\@[0-9a-z\.\-\_]+(\.[0-9a-z\.\-\_]+){1,4}')


@api
@post('api/users')
def register_user():
    i = ctx.request.input(name='',email='',password='')
    name = i.name.strip()
    email = i.email.strip().lower()
    password = i.password
    if not name:
        raise 'name is wrong'
    if not email or not _RE_EMAIL.match(email):
        raise 'email is wrong'
    if not password or _RE_MD5.match(password):
        raise 'password is wrong'
    user = User.find_first('where email=?',email)
    if user:
        raise 'email has already existed'
    user = User(name = name,email=email,password=password,image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest(),admin = 1)
    user.insert()
    return user

@view('register.html')
@get('/register')
def register():
    return dict()





if __name__ == '__main__':
    print _get_page_index()