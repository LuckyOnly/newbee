# coding:utf-8

from transwarp.web import get, view,ctx,post,interceptor
from models import User, Blog, Comment
from apis import api,Page,APIValueError
from  configs import configs
import time,logging
_COOKIE_NAME='zongff'
_COOKIE_KEY=configs['session']['secret']

def make_signed_cookie(id,password,max_age):
    expires = str(int(time.time())+ (max_age or 86400))
    L = [id,expires,hashlib.md5('%s-%s-%s-%s' % (id,password,expires,_COOKIE_KEY)).hexdigest()]
    return '-'.join(L)

def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split('-')
        if len(L)!=3:
            return None
        id , expires, md5=L
        if int(expires)<time.time():
            return None
        user = User.get(id)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (id,user.password,expires,_COOKIE_KEY)).hexdigest():
            return None
        return user
    except:
        return None


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

@interceptor('/')
def user_interceptor(next):
    logging.info('try to bind user from session cookie...')
    user=None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        logging.info('parse session cookie')
        user = parse_signed_cookie(cookie)
        if user:
            logging.info('bind user <%s> to seesion...' % user.email)
    ctx.request.user=user
    return next()

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
@get('/')
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

# 添加cookie
@api
@post('/api/authenticate')
def authenticate():
    i = ctx.request.input(remeber='')
    email = i['email'].strip().lower()
    password = i['password']
    remeber = i['remeber']
    user = User.find_first('where email=?',email)
    if user is None:
        raise APIValueError('auth:failed','email','Invalid email')
    elif user.password != password:
        raise APIValueError('auth: failed','password','Invalid password')
    max_age = 604800 if remeber == 'true' else None
    cookie = make_signed_cookie(user.id,user.password,max_age=max_age)
    user.password = '******'
    return user

import re,hashlib
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')
_RE_EMAIL = re.compile(r'[0-9a-z\.\-\_]+\@[0-9a-z\.\-\_]+(\.[0-9a-z\.\-\_]+){1,4}')

#注册
@api
@post('/api/users')
def register_user():
    i = ctx.request.input(name='',email='',password='')
    print i
    # i = {'password': u'c8837b23ff8aaa8a2dde915473ce0991', 'name': u'3', 'email': u'11047670764@qq.com'}
    name = i['name'].strip()
    email = i['email'].strip().lower()
    password = i['password']
    print name, email, password
    if not name:
        raise APIValueError('name is wrong')
    # if not email or not _RE_EMAIL.match(email):
    #     raise APIValueError('email is wrong')
    # if not password or _RE_MD5.match(password):
    #     raise APIValueError('password is wrong')
    user = User.find_first('where email=?',email)
    if user:
        raise APIValueError('email has already existed')
    user = User(name = name,email=email,password=password,image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest(),admin = 1)
    user.insert()
    cookie = make_signed_cookie(user.id,user.password,None)
    ctx.response.set_cookie(_COOKIE_NAME,cookie)
    return user

@api
@post('/api/blogs')
def api_create_blog():
    i = ctx.request.input(name='',summary='',content='')
    name = i['name'].strip()
    summary = i['summary'].strip()
    content = i['content'].strip()
    if not name:
        raise APIValueError('name is wrong')
    if not summary:
        raise APIValueError('summary is wrong')
    if not content:
        raise APIValueError('content is wrong')
    user = ctx.request.user
    blog = Blog(user_id=user.id,user_name=user.name,name=name,summary=summary,content=content)
    blog.insert()
    return blog



@view('register.html')
@get('/register')
def register():
    return dict()

@view('manage_blog_edit.html')
@get('/manage/blogs/create')
def blogs():
    return dict(id=None, action='/api/blogs', redirect='/manage/blogs', user=ctx.request.user)





if __name__ == '__main__':
    print _get_page_index()