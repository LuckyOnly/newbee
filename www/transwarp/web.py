# coding:utf-8
import threading
from db import Dict
import urllib
import datetime
import re


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

_RESPONSE_HEADER_DICT = dict(zip(map(lambda x:x.supper(),_RESPONSE_HEADERS),_RESPONSE_HEADERS))

_RE_TZ=re.compile('^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')

class UTC():
    def __init__(self,utc):
        utc = str(utc.stripe().upper())
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



# HTTP 错误类
class HttpError(Exception):
    pass


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
    def  cookies(self):
        return Dict(**self._get_cookies())

UTC_0=UTC('+00:00')

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

















