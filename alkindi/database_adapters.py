
import MySQLdb

from sqlbuilder.smartsql import Q, T, Query, Result
from sqlbuilder.smartsql.compilers.mysql import compile as mysql_compile


class ModelError(RuntimeError):
    pass


class MysqlAdapter:

    tables = T

    def __init__(self, **kwargs):
        self.db = MySQLdb.connect(**kwargs)
        self.result = Result(mysql_compile)
        self.log = True

    def query(self, *args):
        return Q(*args, result=self.result)

    def execute(self, query):
        if type(query) == Query:
            (stmt, values) = mysql_compile(query)
        elif type(query) == tuple:
            (stmt, values) = query
        else:
            raise "invalid query type: {}".format(query)
        try:
            if self.log:
                print("[SQL] {};".format(stmt % tuple(values)))
            cursor = self.db.cursor()
            cursor.execute(stmt, values)
            return cursor
        except MySQLdb.IntegrityError as ex:
            raise ModelError(ex)
        except (MySQLdb.OperationalError,
                MySQLdb.DataError,
                MySQLdb.ProgrammingError,
                MySQLdb.InternalError,
                MySQLdb.NotSupportedError) as ex:
            print("Bad SQL statement: {}".format(stmt))
            raise ModelError(ex)

    def first(self, query):
        cursor = self.execute(query[0:1])
        value = cursor.fetchone()
        cursor.close()
        return value

    def insert(self, query):
        self.execute(query).close()
        cursor = self.db.cursor()
        cursor.execute('SELECT last_insert_id();')
        id = cursor.fetchone()
        cursor.close()
        return None if id is None else id[0]

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.close()
