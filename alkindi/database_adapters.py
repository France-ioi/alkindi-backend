
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

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.close()
