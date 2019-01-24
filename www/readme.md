后端API包括：
获取账号：GET /api/accounts

创建账号：POST /api/accounts/create

查询账号：POST /api/accounts/find

（未实现）获取日志：GET /api/blogs

创建日志：POST /api/blogs

（未实现）修改日志：POST /api/blogs/:blog_id

（未实现）删除日志：POST /api/blogs/:blog_id/delete

获取评论：GET /api/comments

（未实现）创建评论：POST /api/blogs/:blog_id/comments

删除评论：POST /api/comments/:comment_id/delete

创建新用户：POST /api/users

(未实现)获取用户：GET /api/users

管理页面包括：
添加账户页：GET /manage/accounts/create

账户列表页：GET /manage/accounts

评论列表页：GET /manage/comments

日志列表页：GET /manage/blogs

创建日志页：GET /manage/blogs/create

（未实现）修改日志页：GET /manage/blogs/

（未实现）用户列表页：GET /manage/users

用户浏览页面包括：

注册页：GET /register

登录页：GET /signin

注销页：GET /signout

首页：GET /

日志详情页：GET /blog/:blog_id