# coding:utf-8
import logging
# 数据库引擎对象
import ConfigParser
import os
import sys
import threading
import functools
reload(sys)
sys.setdefaultencoding('utf-8')
# get the database configure
cf = ConfigParser.ConfigParser()
path = os.path.dirname(os.path.abspath(__file__))
cf.read(path+r'\db1.cfg')
secs = cf.sections()
host = cf.get('db', 'host')
user = cf.get('db', 'username')
password = cf.get('db', 'passwd')
database = cf.get('db', 'database')
port = int(cf.get('db', 'port'))


class Dict(dict):
    def __init__(self,names=(),values=(),**kw):
        super(Dict,self).__init__(**kw)
        for k,v in zip(names,values):
            self[k]=v

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % item)

    def __setattr__(self, key, value):
        self[key]=value


class _LasyConnection(object):

    def __init__(self):
        self.connection = None

    def cursor(self):
        if self.connection is None:
            connection = engine.connect()
            logging.info('open connection <%s>...' % hex(id(connection)))
            self.connection=connection
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def cleanup(self):
        if self.connection:
            connection = self.connection
            self.connection=None
            logging.info('close connection')
            connection.close()

class _DbCtx(threading.local):

    # Thread local object that holds connection info.
    def __init__(self):
        self.connection = None
        self.transactions =0

    def is_init(self):
        return not self.connection is None

    def init(self):
        logging.info('open lazy connection...')
        self.connection = _LasyConnection()
        self.transactions =0

    def cleanup(self):
        self.connection.cleanup()
        self.connection=None

    def cursor(self):
        return self.connection.cursor()





class _TransactionCtx(object):

    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transactions = _db_ctx.transactions +1
        logging.info('begin transaction...' if _db_ctx.transactions==1 else 'join current transaction...')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions -1
        try:
            if _db_ctx.transactions==0:
                if exc_type is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            if self.should_close_conn:
                _db_ctx.cleanup()

    def commit(self):

        global _db_ctx
        logging.info('commit transactions...')
        try:
            _db_ctx.connection.commit()
            logging.info('commit ok.')
        except:
            logging.warning('commit failed. try rollback...')
            _db_ctx.connection.rollback()
            logging.info('rollback ok.')
            raise

    def rollback(self):

        global _db_ctx
        logging.warning('rollback transaction...')
        _db_ctx.connection.rollback()
        logging.info('rollback ok.')


def with_transaction(func):

    @functools.wraps(func)
    def _wrapper(*args,**kw):
        with _TransactionCtx():
            return func(*args,**kw)
    return _wrapper

_db_ctx = _DbCtx()

engine = None

class _Engine(object):
    def __init__(self,connect):
        self._connect = connect

    def connect(self):
        return self._connect()



def create_engine(user, password, database, host, port, **kw):
    import MySQLdb
    import mysql.connector
    global engine
    if engine is not None:
        logging.info('Engine is already initialized.')
    params = dict(user=user,password=password,database=database,host=host,port=port)
    defaluts = dict(use_unicode=True,charset='utf8',collation='utf8_general_ci',autocommit=False)
    for k,v in defaluts.iteritems():
        params[k]=kw.pop(k,v)
    params.update(kw)
    params['buffered']=True
    # engine = _Engine(lambda :MySQLdb.connect(**params))
    engine = _Engine(lambda :mysql.connector.connect(**params))
    # engine = mysql.connector.connect(**params)
    logging.info('init mysql engine <%s> ok'% hex(id(engine)))
#数据库连接上下文对象


class _ConnectionCtx(object):
    '''
    _ConnectionCtx object that can open and close connection context. _ConnectionCtx object can be nested and only the most 
    outer connection has effect.
    '''

    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()


def connection():

    '''
       Return _ConnectionCtx object that can be used by 'with' statement:

       with connection():
           pass
       '''
    return _ConnectionCtx()


def with_connection(func):

    @functools.wraps(func)
    def _wrapper(*args,**kw):
        with _ConnectionCtx():
            return func(*args,**kw)
    return _wrapper


@with_connection
def _update(sql, *args):
    global _db_ctx
    cursor = None
    sql = sql.replace('?','%s')
    logging.info('sql:%s,args:%s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        r = cursor.rowcount
        if _db_ctx.transactions == 0:
            logging.info('auto commit')
            _db_ctx.connection.commit()
        return r
    except Exception as e:
        logging.info(e)
    finally:
        if cursor:
            cursor.close()

@with_connection
def _select(sql,first,*args):
    global _db_ctx
    cursor = None
    sql = sql.replace('?','%s')
    logging.info('sql:%s,args:%s' % (sql,args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql,args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if first:
            values = cursor.fetchone()
            if not values:
                return None
            return Dict(names,values)
        return [Dict(names,x) for x in cursor.fetchall()]
    finally:
        if cursor:
            cursor.close()

def select(sql,*args):
    return _select(sql,False,*args)

def update(sql,*args):

    return _update(sql,*args)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    create_engine(user=user,password=password,database=database,host=host,port=port)
    u = select('select * from department where id = ?',1)
    print u
    u2 = select('select * from department where id = ?', 2)
    print u2
    update('drop table if exists user')
    update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')
    # import doctest
    # doctest.testmod()