# coding:utf-8

from transwarp.web import get, view,ctx
from models import User, Blog, Comment
from apis import api,Page


def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page','1'))
    except ValueError:
        pass
    return page_index

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

@view('blogs.html')
@get('/blogs')
def index():
    blogs = Blog.find_all("where 1=1")
    total = Blog.count_all()
    page = Page(total)
    # 查找登陆用户:
    user = User.find_first('where email=?', 'admin@example.com')
    return dict(blogs=blogs, user=user,page=page)

@api
@get('/api/users')
def api_get_users():
    total = User.count_all()
    # page = Page(total,_get_page_index())
    page = Page(total)
    users = User.find_by('order by created_at desc limit ?,?',page.offset,page.limit)
    for u in users:
        u.password = "****"
    return dict(users=users,page=page)



if __name__ == '__main__':
    print _get_page_index()