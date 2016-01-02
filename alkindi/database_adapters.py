
import mysql.connector as mysql

from sqlbuilder.smartsql import Q, T, Query, Result
from sqlbuilder.smartsql.compilers.mysql import compile as mysql_compile


class ModelError(RuntimeError):
    pass


class MysqlAdapter:

    tables = T

    def __init__(self, **kwargs):
        self.db = mysql.connect(**kwargs)
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
        except mysql.IntegrityError as ex:
            raise ModelError(ex)
        except (mysql.OperationalError,
                mysql.DataError,
                mysql.ProgrammingError,
                mysql.InternalError,
                mysql.NotSupportedError) as ex:
            print("Bad SQL statement: {}".format(stmt))
            raise ModelError(ex)

    def scalar(self, query):
        cursor = self.execute(query)
        row = cursor.fetchone()
        cursor.close()
        return row[0]

    def first(self, query):
        cursor = self.execute(query[0:1])
        row = cursor.fetchone()
        cursor.close()
        return row

    def delete(self, query, **kwargs):
        cursor = self.execute(query.delete(**kwargs))
        cursor.close()

    def update(self, query, attrs):
        cursor = self.execute(query.update(attrs))
        cursor.close()

    def all(self, query):
        cursor = self.execute(query)
        row = cursor.fetchone()
        while row is not None:
            yield row
            row = cursor.fetchone()
        cursor.close()

    def insert(self, query):
        self.execute(query).close()
        cursor = self.db.cursor()
        cursor.execute('SELECT last_insert_id();')
        id = cursor.fetchone()
        cursor.close()
        return None if id is None else id[0]

    def rollback(self):
        self.db.rollback()

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.close()

    def view_bool(self, value):
        return value != 0
