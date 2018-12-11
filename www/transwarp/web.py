# coding:utf-8
import threading
from db import Dict
import urllib
import datetime
import re
import functools
import logging
import types
import os, mimetypes,sys,traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


# 全局ThreadLocal对象
ctx = threading.local()

_RESPONSE_HEADERS =(
    'Accept-Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy-Authenticate',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Powered-By',
    'X-UA-Compatible',
)

_RESPONSE_HEADER_DICT = dict(zip(map(lambda x:x.upper(),_RESPONSE_HEADERS),_RESPONSE_HEADERS))

_RE_TZ=re.compile('^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')

class UTC(datetime.tzinfo):
    def __init__(self,utc):
        utc = str(utc.strip().upper())
        mt = _RE_TZ.match(utc)
        if mt:
            minus = mt.group(1)=='-'
            h = int(mt.group(2))
            m = int(mt.group(3))
            if minus:
                h,m=(-h),(-m)
                self._utcoffset = datetime.timedelta(hours=h,minutes=m)
                self._tzname ="UTC%s" % utc
            else:
                raise ValueError('bad utc time zone')

    def __str__(self):
        return 'UTC tzinfo object (%s)' % self._tzname

_HEADER_X_POWERED_BY = ('X-Powered-By', 'transwarp/1.0')


# HTTP 错误类
class HttpError(Exception):
    def __init__(self, code):
        '''
        Init an HttpError with response code.
        '''
        super(HttpError, self).__init__()
        self.status = '%d %s' % (code, _RESPONSE_STATUSES[code])

    def header(self, name, value):
        if not hasattr(self, '_headers'):
            self._headers = [_HEADER_X_POWERED_BY]
        self._headers.append((name, value))

    @property
    def headers(self):
        if hasattr(self, '_headers'):
            return self._headers
        return []

    def __str__(self):
        return self.status

    __repr__ = __str__



def _to_unicode(s,encoding='utf-8'):
    return s.decode(encoding)

def _unquote(s,encoding='utf-8'):
    return urllib.unquote(s).decode(encoding)

def _to_str(s):
    if isinstance(s,str):
        return s
    if isinstance(s.unicode):
        return s.encode('utf-8')
    return str(s)

def _quote(s,encoding='utf-8'):
    if isinstance(s,unicode):
        s = s.encode(encoding)
    return urllib.quote(s)


class MultipartFile(object):
    def __init__(self,storage):
        self.filename = _to_unicode(storage.filename)
        self.file = storage.file

# request对象
class Request(object):

    def __init__(self,environ):
        self._environ = environ
    # 格式化
    def _parse_input(self):
        def _convert(item):
            if isinstance(item, list):
                return [_to_unicode(i.value) for i in item]
            if item.filename:
                return MultipartFile(item)
            return _to_unicode(item.value)
    # 原始输入
    def _get_raw_input(self):
        if not hasattr(self,'_raw_input'):
            self._raw_input = self._parse_input()
        return self._raw_input

    # 根据key返回value
    def get(self,key,default=None):
        r = self._get_raw_input().get(key,default)
        if isinstance(r,list):
            return r[0]
        return r

    # 返回key-value的dict
    def input(self, **kw):
        copy = Dict(**kw)
        raw = self._get_raw_input()
        for k,v in raw.iteritems():
            copy[0] = v[0] if isinstance(v.list) else v
        return copy

    # 获取request path
    @property
    def path_info(self):
        return urllib.unquote(self._environ.get('PATH_INFO',''))

    def _get_headers(self):
        if not hasattr(self,'_headers'):
            hdrs = {}
            for k,v in self._environ.iteritems():
                if k.startswith('HTTP_'):
                    hdrs[k[5:].replace('_','-').upper()] = v.decode('utf-8')
            self._headers = hdrs
        return self._headers

    # 返回HTTP header
    @property
    def headers(self):
        return Dict(**self._get_headers())

    def _get_cookies(self):
        if not hasattr(self,'_cookies'):
            cookies = {}
            cookie_str = self._environ.get('HTTP_COOKIE')
            if cookie_str:
                for c in cookie_str.split(';'):
                    pos = c.find('=')
                    if pos>0:
                        cookies[c[:pos].strip()] = _unquote(c[pos+1:])
            self._cookies = cookies
        return self._cookies

    # 根据key返回cookie
    @property
    def cookies(self):
        return Dict(**self._get_cookies())

    @property
    def request_method(self):
        return self._environ['REQUEST_METHOD']

UTC_0=UTC('-00:00')

_RESPONSE_STATUSES= {
    # Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',

    # Successful
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',

    # Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    # Client Error
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',

    # Server Error
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended',
}

_RE_RESPONSE_STATUSE = re.compile(r'^\d\d\d(\ [\w\ ]+)?$')

# response对象
class Response(object):

    def __init__(self):
        self._status = '200 OK'
        self._headers = {'CONTENT-TYPE':'text/html; charset=utf-8'}

    def set_header(self,name,value):
        key = name.upper
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        self._headers[key]=_to_str(value)

    # 设置Cookie
    def set_cookie(self,name,value,max_age=None,expires = None,path='/',domain=None,secure=False,http_only=True):
        if not hasattr(self,'_cookies'):
            self._cookies={}
        L = ['%s=%s' % (_quote(name),_quote(value))]
        if expires is not None:
            if isinstance(expires,(float,int,long)):
                L.append('Expires=%s' % datetime.datetime.fromtimestamp(expires,UTC_0).strftime('%a,%d-%b-%Y %H:%M:%S GMT'))
            if isinstance(expires,(datetime.date,datetime.datetime)):
                L.append('Expires=%s' % datetime.datetime.astimezone(UTC_0).strftime('%a,%d-%b-%Y %H:%M:%S GMT'))
        elif isinstance(max_age,(int,long)):
            L.append('Max-Age=%d' % max_age)
        L.append('Path=%s' % path)
        if domain:
            L.append('Domain=%s' % domain)
        if secure:
            L.append('Secure')
        if http_only:
            L.append('HttpOnly')
        self._cookies[name]=','.join(L)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self,value):
        if isinstance(value,(int,long)):
            if value>=100 and value<=999:
                st = _RESPONSE_STATUSES.get(value,'')
                if st:
                    self._status = '%d %s' % (value, st)
                else:
                    self._status = str(value)
            else:
                raise ValueError('Bad response code: %d' % value)
        elif isinstance(value, basestring):
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if _RE_RESPONSE_STATUSE.match(value):
                self._status = value
            else:
                raise TypeError('Bad type of response code.')

    @property
    def headers(self):
        L = [(_RESPONSE_HEADER_DICT.get(k, k), v) for k, v in self._headers.iteritems()]
        if hasattr(self, '_cookies'):
            for v in self._cookies.itervalues():
                L.append(('Set-Cookie', v))
        L.append(_HEADER_X_POWERED_BY)
        return L




class Template(object):
    def __init__(self,template_name, **kw):
        self.template_name = template_name
        self.model = dict(**kw)

def get(path):
    def _decorator(func):
        func.__web_route__ = path
        func.__web_method__ = 'GET'
        return func
    return _decorator

def post(path):
    def _decorator(func):
        func.__web_route__ = path
        func.__web_method__ = 'POST'
        return func
    return _decorator

# 定义模板
def view(path):
    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args,**kw):
            r = func(*args,**kw)
            if isinstance(r,dict):
                logging.info('return Template')
                return Template(path,**r)
            raise ValueError('Except return a dict when using @value() decorator')
        return _wrapper
    return _decorator

_RE_INTERCEPTROR_STARTS_WITH = re.compile(r'^([^\*\?]+)\*?$')
_RE_INTERCEPTROR_ENDS_WITH = re.compile(r'^\*([^\*\?]+)$')

def _build_pattern_fn(pattern):
    m = _RE_INTERCEPTROR_STARTS_WITH.match(pattern)
    if m:
        return lambda p:p.startswith(m.group(1))
    m=_RE_INTERCEPTROR_ENDS_WITH.match(pattern)
    if m:
        return lambda p:p.endswith(m.group(1))
    raise ValueError('Invalid pattern definition in interceptor')

#定义拦截器
def interceptor(pattern):
    def _decorator(func):
        func.__interceptor__ = _build_pattern_fn(pattern)
        return func
    return _decorator

class TemplateEngine(object):
    def __call__(self, *args, **kwargs):
        return '<!-- override this method to render template -->'

def _load_module(module_name):
    last_dot = module_name.rfind('.')
    if last_dot == (-1):
        return __import__(module_name,globals(), locals())
    from_module = module_name[:last_dot]
    import_module = module_name[last_dot+1:]
    m = __import__(from_module,globals(),locals(),[import_module])
    return getattr(m, import_module)


class Jinja2TemplateEngine(TemplateEngine):
    def __init__(self,teml_dir, **kw):
        from jinja2 import Environment, FileSystemLoader
        if not "autoescape" in kw:
            kw['autoescape'] = True
        self._env = Environment(loader=FileSystemLoader(teml_dir),**kw)

    def add_filter(self,name, fn_filter):
        self._env.filters[name] = fn_filter

    def __call__(self, args, kwargs):
        return self._env.get_template(args).render(**kwargs).encode('utf-8')

_re_route = re.compile(r'(\:[a-zA-Z_])')
def _build_regex(path):
    re_list = ['^']
    var_list =[]
    is_var = False
    for v in _re_route.split(path):
        if is_var:
            var_name = v[1:]
            var_list.append(var_name)
            re_list.append(r'(?P<%s[^\/]+>)' % var_name)
        else:
            s = ''
            for ch in v:
                if ch>='0' and ch<='9':
                    s = s+ch
                elif ch>='A' and ch<='Z':
                    s = s+ch
                elif ch>='s' and ch<='z':
                    s = s+ch
                else:
                    s = s+'\\'+ch
            re_list.append(s)
        is_var = not is_var
    re_list.append('$')
    return ''.join(re_list)

def notfound():
    return HttpError(404)

def _static_file_generator(fpath):
    BLOCK_SIZE = 8192
    with open(fpath, 'rb') as f:
        block = f.read(BLOCK_SIZE)
        while block:
            yield block
            block = f.read(BLOCK_SIZE)

def badrequest():
    return HttpError(400)

def _build_interceptor_fn(func, next):
    def _wrapper():
        if func.__interceptor__(ctx.request.path_info):
            return func(next)
        else:
            return next()
    return _wrapper

def _build_interceptor_chain(last_fn, *interceptors):
    L = list(interceptors)
    L.reverse()
    fn = last_fn
    for f in L:
        fn = _build_interceptor_fn(f, fn)
    return fn

class Route(object):
    def __init__(self,func):
        self.path = func.__web_route__
        self.method = func.__web_method__
        self.is_static = _re_route.search(self.path) is None
        if not self.is_static:
            self.route = re.compile(_build_regex(self.path))
        self.func = func

    def match(self, url):
        m = self.route.match(url)
        if m:
            return m.groups()
        return None

    def __call__(self, *args):
        return self.func(*args)

    def __str__(self):
        if self.is_static:
            return 'Route(static,%s,path=%s)' % (self.method, self.path)
        return 'Route(dynamic,%s,path=%s)' % (self.method, self.path)

    __repr__ = __str__

class RedirectError(HttpError):
    def __init__(self, code, location):
        '''
        Init an HttpError with response code.
        '''
        super(RedirectError, self).__init__(code)
        self.location = location

    def __str__(self):
        return '%s, %s' % (self.status, self.location)

    __repr__ = __str__



class StaticFileRoute(object):

    def __init__(self):
        self.method = 'GET'
        self.is_static = False
        self.route = re.compile('^/static/(.+)$')

    def match(self, url):
        if url.startswith('/static/'):
            return (url[1:], )
        return None

    def __call__(self, *args):
        fpath = os.path.join(ctx.application.document_root, args[0])
        if not os.path.isfile(fpath):
            raise notfound()
        fext = os.path.splitext(fpath)[1]
        ctx.response.content_type = mimetypes.types_map.get(fext.lower(), 'application/octet-stream')
        return _static_file_generator(fpath)


class WSGIApplication(object):
    def __init__(self,document_root = None ,**kw):
        self._running = False
        self._document_root = document_root
        self._interceptors = []
        self._template_engine = None
        self._get_static = {}
        self._post_static = {}
        self._get_dynamic=[]
        self._post_dynamic = []

    def _check_not_running(self):
        if self._running:
            raise RuntimeError('Cannot modify WSGIApplication when running.')

    @property
    def template_engine(self):
        return self._template_engine

    @template_engine.setter
    def template_engine(self,engine):
        self._check_not_running()
        self._template_engine =engine

    def add_module(self,mod):
        self._check_not_running()
        m = mod if type(mod) == types.ModuleType else _load_module(mod)
        logging.info('Add module: %s' % m.__name__)
        for name in dir(m):
            fn = getattr(m, name)
            if callable(fn) and hasattr(fn,'__web_route__') and hasattr(fn,'__web_method__'):
                self.add_url(fn)

    def add_url(self,func):
        self._check_not_running()
        route = Route(func)
        if route.is_static:
            if route.method == 'GET':
                self._get_static[route.path] = route
            if route.method == 'POST':
                self._post_static[route.path] = route
        else:
            if route.method == 'GET':
                self._get_dynamic.append(route)
            if route.method == 'POST':
                self._post_dynamic.append(route)
        logging.info('Add route: %s' % str(route))

    def run(self, port = 9000, host='127.0.0.1'):
        from wsgiref.simple_server import make_server
        logging.info('application (%s) will start at %s:%s...' % (self._document_root, host, port))
        server = make_server(host,port,self.get_wsgi_application(debug=True))
        server.serve_forever()

    def get_wsgi_application(self,debug = False):
        self._check_not_running()
        if debug:
            self._get_dynamic.append(StaticFileRoute())
        self._running = True
        _application = Dict(document_root=self._document_root)

        def fn_route():
            request_method = ctx.request.request_method
            path_info = ctx.request.path_info
            if request_method=='GET':
                fn = self._get_static.get(path_info, None)
                if fn:
                    return fn()
                for fn in self._get_dynamic:
                    args = fn.match(path_info)
                    if args:
                        return fn(*args)
                raise notfound()
            if request_method=='POST':
                fn = self._post_static.get(path_info, None)
                if fn:
                    return fn()
                for fn in self._post_dynamic:
                    args = fn.match(path_info)
                    if args:
                        return fn(*args)
                raise notfound()
            raise badrequest()

        fn_exec = _build_interceptor_chain(fn_route, *self._interceptors)

        def wsgi(env, start_response):
            ctx.application = _application
            ctx.request = Request(env)
            print '环境是',env,start_response
            response = ctx.response = Response()
            try:
                r = fn_exec()
                if isinstance(r, Template):
                    r = self._template_engine(r.template_name, r.model)
                if isinstance(r, unicode):
                    r = r.encode('utf-8')
                if r is None:
                    r = []
                start_response(response.status, response.headers)
                return r
            except RedirectError, e:
                response.set_header('Location', e.location)
                start_response(e.status, response.headers)
                return []
            except HttpError, e:
                start_response(e.status, response.headers)
                return ['<html><body><h1>', e.status, '</h1></body></html>']
            except Exception, e:
                logging.exception(e)
                if not debug:
                    start_response('500 Internal Server Error', [])
                    return ['<html><body><h1>500 Internal Server Error</h1></body></html>']
                exc_type, exc_value, exc_traceback = sys.exc_info()
                fp = StringIO()
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=fp)
                stacks = fp.getvalue()
                fp.close()
                start_response('500 Internal Server Error', [])
                return [
                    r'''<html><body><h1>500 Internal Server Error</h1><div style="font-family:Monaco, Menlo, Consolas, 'Courier New', monospace;"><pre>''',
                    stacks.replace('<', '&lt;').replace('>', '&gt;'),
                    '</pre></div></body></html>']
            finally:
                del ctx.application
                del ctx.request
                del ctx.response

        return wsgi

def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        pass
    return page_index

if __name__=='__main__':
    import time
    print time.time()










