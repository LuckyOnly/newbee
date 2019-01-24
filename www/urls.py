# coding:utf-8

from transwarp.web import get, view, ctx, post, interceptor, seeother
from models import User, Blog, Comment, Accounts
from apis import api, Page, APIValueError, APIError, APIPermissionError, APIResourceNotFoundError
from configs import configs
import time
import logging
import re, hashlib
import urllib

_COOKIE_NAME = 'zongff'
_COOKIE_KEY = configs['session']['secret']


def make_signed_cookie(user_id, password, max_age):
    expires = str(int(time.time()) + (max_age or 86400))
    signed_cookie = [user_id, expires,
                     hashlib.md5('%s-%s-%s-%s' % (user_id, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(signed_cookie)


def parse_signed_cookie(cookie_str):
    try:
        cookie_list = cookie_str.split('-')
        if len(cookie_list) != 3:
            return None
        user_id, expires, md5 = cookie_list
        if int(expires) < time.time():
            return None
        user = User.get(user_id)
        # logging.info('password', user.password)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (user_id, user.password, expires, _COOKIE_KEY)).hexdigest():
            return None
        return user
    except EOFError as e:
        return None


def check_admin():
    user = ctx.request.user
    print user
    if user and user.admin:
        return
    raise APIPermissionError('No permission')


def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        # page_index = 1
        pass
    return page_index


def _get_blogs_by_page():
    total = Blog.count_all()
    page = Page(total, _get_page_index())
    blogs = Blog.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return blogs, page


_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')
_RE_EMAIL = re.compile(r'[0-9a-z\.\-\_]+\@[0-9a-z\.\-\_]+(\.[0-9a-z\.\-\_]+){1,4}')


def _get_accounts_by_page():
    total = Accounts.count_all()
    page = Page(total, _get_page_index())
    print page
    accounts = Accounts.find_all('order by created_at desc limit ?,?', page.offset, page.limit)
    return accounts, page


@interceptor('/')
def user_interceptor(is_next):
    logging.info('try to bind user from session cookie...')
    user = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        logging.info('parse session cookie...')
        user = parse_signed_cookie(cookie)
        if user:
            logging.info('bind user <%s> to session...' % user.email)
    ctx.request.user = user
    return is_next()


@interceptor('/manage/')
def manage_interceptor(is_next):
    user = ctx.request.user
    if user and user.admin:
        return is_next()
    raise seeother('/signin')


@api
@get('/get/blogs')
def api_get_blogs():
    blogs, page = _get_blogs_by_page()
    return dict(blogs=blogs, page=page)


# 日志列表页
@view('manage_blog_list.html')
@get('/manage/blogs')
def manage_blogs():
    # return dict(page_index=_get_blogs_by_page(),user=ctx.request.user)
    return dict(page_index=_get_blogs_by_page())


# @api
# @post('/api/comments/:comment_id/delete')
# def api_delete_comment(comment_id):
#     check_admin()
#     comment = Comment.get(comment_id)
#     if comment is None:
#         raise APIValueError('comment')
#     comment.delete()
#     raise dict(id=comment_id)



# @view('test_users.html')
@get('/demo')
def test_users():
    users = User.find_first('where admin = ?', 0)
    # return dict(users=users)
    return '<h1>hello</h1>'


@view('test_users.html')
@get('/test')
def test_users():
    users = User.find_first('where admin = ?', 0)
    return dict(users=users)


@view('blogs.html')
@get('/123')
def index():
    blogs, page = _get_blogs_by_page()
    return dict(page=page, blogs=blogs, user=ctx.request.user)


# 首页
@view('blogs.html')
@get('/')
def index():
    blogs = Blog.find_all("where 1=1")
    total = Blog.count_all()
    page = Page(total)
    # 查找登陆用户:
    user = User.find_first('where email=?', 'admin@example.com')
    return dict(blogs=blogs, user=user, page=page)


@get('/manage/')
def manage_index():
    raise seeother('/manage/comments')


@api
@get('/api/user')
def api_get_users():
    total = User.count_all()
    # page = Page(total,_get_page_index())
    page = Page(total)
    users = User.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    for u in users:
        u.password = "****"
    return dict(users=users, page=page)


# 添加cookie
@api
@post('/api/authenticate')
def authenticate():
    i = ctx.request.input(remember='')
    email = i['email'].strip().lower()
    password = i['password']
    remember = i['remember']
    user = User.find_first('where email=?', email)
    if user is None:
        raise APIError('auth:failed', 'email', 'Invalid email')
    elif user.password != password:
        raise APIError('auth: failed', 'password', 'Invalid password')
    max_age = 604800 if remember == 'true' else None
    cookie = make_signed_cookie(user.id, user.password, max_age=max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)
    user.password = '******'
    print user.password
    return user


# 注册api
@api
@post('/api/users')
def register_user():
    i = ctx.request.input(name='', email='', password='')
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
    user = User.find_first('where email=?', email)
    if user:
        raise APIValueError('email has already existed')
    user = User(name=name, email=email, password=password,
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest(), admin=1)
    user.insert()
    cookie = make_signed_cookie(user.id, user.password, None)
    ctx.response.set_cookie(_COOKIE_NAME, cookie)
    return user

@api
@post('/api/accounts/create')
def api_create_accounts():
    i = ctx.request.input(name='',url='',accname='',passwd='',admin='',detail='')
    name = i['name'].strip()
    url=i['url'].strip()
    accname =i['accname'].strip()
    passwd = i['passwd'].strip()
    admin = i['admin'].strip()
    detail = i['detail'].strip()
    account_insert = Accounts(name=name,url=url,accname=accname,passwd=passwd,admin=admin,detail=detail)
    account_insert.insert()
    return account_insert

@api
@get('/api/accounts/:search/finds')
def accounts_find_by_name(search):
    search=urllib.unquote(search)
    search =search.decode('utf-8')
    sql ="where name like '%"+search+"%'"
    size = Accounts.count_all_by_where(sql)
    page = Page(size, _get_page_index())
    if size>0:
        accounts = Accounts.find_by(sql+' order by created_at desc limit ?,?', page.offset, page.limit)
        return dict(accounts=accounts, page=page)
    else:
        return dict(accounts=False,page=page)


@api
@get('/api/accounts')
def api_get_accounts():
    total = Accounts.count_all()
    page = Page(total, _get_page_index())
    accounts = Accounts.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return dict(accounts=accounts, page=page)

@api
@get('/api/accounts/find')
def api_accounts_find_init():
    total = Accounts.count_all()
    page = Page(total, _get_page_index())
    accounts = Accounts.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return dict(accounts=accounts, page=page)


# 账户列表页
@view('account_find.html')
@get('/manage/accounts')
def find_accounts():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

# # 查询账户列表页
@view('account_find3.html')
@get('/manage/find')
def find_account():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

# 创建日志
@api
@post('/api/blogs')
def api_create_blog():
    i = ctx.request.input(name='', summary='', content='')
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
    blog = Blog(user_id=user.id, user_name=user.name, name=name, summary=summary, content=content)
    blog.insert()
    return blog


# 删除评论api
@api
@post('/api/comments/:comment_id/delete')
def api_delete_comment(comment_id):
    check_admin()
    comment = Comment.get(comment_id)
    if comment is None:
        raise APIResourceNotFoundError('Comment')
    comment.delete()
    return dict(id=comment_id)

@api
@post('/api/accounts/:comment_id/delete')
def api_delete_comment_by_id(comment_id):
    check_admin()
    comment = Accounts.get(comment_id)
    if comment is None:
        raise APIResourceNotFoundError('Comment')
    comment.delete()
    return dict(id=comment_id)


# 获取评论
@api
@get('/api/comments')
def api_get_comments():
    total = Comment.count_all()
    page = Page(total, _get_page_index())
    comments = Comment.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return dict(comments=comments, page=page)


# 登录页
@view('signin.html')
@get('/signin')
def signin():
    return dict()


# 注销页
@get('signout')
def signout():
    ctx.response.delete_cookie(_COOKIE_NAME)
    raise seeother('/')


# 注册页
@view('register.html')
@get('/register')
def register():
    return dict()


@get('/manage/')
def manage_index():
    raise seeother('/manage/comments')


# 评论列表页
@view('manage_comment_list.html')
@get('/manage/comments')
def manage_comments():
    return dict(page_index=_get_page_index(), user=ctx.request.user)


# 创建日志页
@view('manage_blog_edit.html')
@get('/manage/blogs/create')
def blogs():
    return dict(id=None, action='/api/blogs', redirect='/manage/blogs', user=ctx.request.user)


# 创建账号页
@view('account_add.html')
@get('/manage/accounts/create')
def account_create():
    return dict(id=None, action='/api/accounts/create', redirect='/manage/accounts', user=ctx.request.user)


if __name__ == '__main__':
    print _get_accounts_by_page()
