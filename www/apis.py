# coding:utf-8
import functools
import json
import logging
from transwarp.web import ctx

class Page(object):
    def __init__(self,item_count,page_index=1,page_size = 15):
        # item_count:总页数, page_count:总页数, page_index: 当前所在页, offset:当前页的第一个编号, limit:每页展示的个数
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size+(1 if item_count % page_size >0 else 0)
        if (item_count == 0) or (page_index <1) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index-1)
            self.limit = self.page_size
        self.has_next = self.page_index<self.page_count
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count:%s, page_count:%s, page_index: %s, offset:%s, limit:%s' % (self.item_count,self.page_count,self.page_index,self.offset,self.limit)

    __repr__ = __str__

class APIError(StandardError):
    def __init__(self,error,data='',message=''):
        super(APIError,self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

def _dump(obj):
    if isinstance(obj,Page):
        return {
            'page_index':obj.page_index,
            'page_count':obj.page_count,
            'item_count':obj.item_count,
            'has_next':obj.has_next,
            'has_previous':obj.has_previous
        }
        raise TypeError('%s is not json serializable' % obj)

def dumps(obj):
    return json.dumps(obj, default=_dump)

def api(func):
    @functools.wraps(func)
    def _wrapper(*args,**kw):
        try:
            r = dumps(func(*args,**kw))
        except APIError, e:
            r = json.dumps(dict(error=e.error,data = e.data,message = e.message))
        except Exception,e:
            logging.exception(e)
            r = json.dumps(dict(error='internalerror',data = e.__class__.__name__,message = e.message))
        ctx.response.content_type ="application/json"
        return r
    return _wrapper

if __name__ =="__main__":
    p = Page(90,9,10)
    print p


