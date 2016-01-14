
import mysql.connector as mysql
from sqlbuilder.smartsql import Q, T, Query, Result
from sqlbuilder.smartsql.compilers.mysql import compile as mysql_compile
import json


class ModelError(RuntimeError):
    pass


class MysqlAdapter:

    tables = T

    def __init__(self, **kwargs):
        self.db = mysql.connect(**kwargs)
        self.result = Result(mysql_compile)
        self.log = True

    def start_transaction(self):
        self.db.start_transaction(
            consistent_snapshot=True,
            isolation_level='REPEATABLE READ')

    def query(self, *args):
        return Q(*args, result=self.result)

    def execute(self, query):
        if type(query) == tuple:
            (stmt, values) = query
        elif type(query) == Query:
            (stmt, values) = mysql_compile(query)
            raise ModelError("invalid query type: {}".format(query))
        try:
            if self.log:
                print("[SQL] {};".format(stmt % tuple(values)))
            cursor = self.db.cursor()
            cursor.execute(stmt, values)
            return cursor
        except mysql.IntegrityError as ex:
            raise ModelError(ex)
        except mysql.OperationalError as ex:
            print("Lost connection to mysql")
            raise ModelError(ex)
        except (mysql.DataError,
                mysql.ProgrammingError,
                mysql.InternalError,
                mysql.NotSupportedError) as ex:
            print("Bad SQL statement: {}".format(stmt))
            raise ModelError(ex)

    def scalar(self, query):
        cursor = self.execute(query)
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row is not None else None

    def first(self, query, for_update=False):
        query = query[0:1].select(for_update=for_update)
        cursor = self.execute(query)
        row = cursor.fetchone()
        cursor.close()
        return row

    def all(self, query, for_update=False):
        query = query.select(for_update=for_update)
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

    def update(self, query, attrs):
        cursor = self.execute(query.update(attrs))
        count = cursor.rowcount
        cursor.close()
        return count

    def delete(self, query, **kwargs):
        cursor = self.execute(query.delete(**kwargs))
        count = cursor.rowcount
        cursor.close()
        return count

    def ensure_connected(self):
        try:
            self.db.ping(reconnect=True, attempts=5, delay=2)
        except mysql.InterfaceError:
            raise ModelError('database is unavailable')

    def rollback(self):
        self.db.rollback()

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.close()

    def load_bool(self, value):
        return value != 0

    def load_json(self, value):
        return json.loads(value)

    def dump_json(self, value):
        return json.dumps(value)

    def load_scalar(self, table, value, column, key=None):
        """ Load the specified `column` from the first row in `table`
            where `by`=`value`.
        """
        key_column = table.id if key is None else getattr(table, key)
        query = self.query(table) \
            .where(key_column == value) \
            .fields(getattr(table, column))
        row = self.first(query)
        return None if row is None else row[0]

    def load_row(self, table, value, columns, key=None, for_update=False):
        key_column = table.id if key is None else getattr(table, key)
        query = self.query(table) \
            .where(key_column == value) \
            .fields(*[getattr(table, col) for col in columns])
        row = self.first(query, for_update=for_update)
        if row is None:
            raise ModelError('no such row')
        return {key: row[i] for i, key in enumerate(columns)}

    def load_rows(self, table, values, columns, key=None, for_update=False):
        if len(values) == 0:
            return []
        key_column = table.id if key is None else getattr(table, key)
        query = self.query(table) \
            .where(key_column.in_(list(values))) \
            .fields(*[getattr(table, col) for col in columns])
        return [
            {key: row[i] for i, key in enumerate(columns)}
            for row in self.all(query, for_update=for_update)
        ]

    def insert_row(self, table, attrs):
        query = self.query(table)
        query = query.insert({
            getattr(table, key): attrs[key] for key in attrs
        })
        return self.insert(query)

    def update_row(self, table, value, attrs, key=None):
        key_column = table.id if key is None else getattr(table, key)
        query = self.query(table) \
            .where(key_column == value) \
            .update({getattr(table, key): attrs[key] for key in attrs})
        cursor = self.execute(query)
        cursor.close()
        return cursor

    def all_rows(self, query, cols):
        rows = [{col[0]: row[i] for i, col in enumerate(cols)}
                for row in self.all(query)]
        for row in rows:
            for col in cols:
                if len(col) == 3:
                    key = col[0]
                    if col[2] == 'bool':
                        row[key] = self.view_bool(row[key])
        return rows

    def log_error(self, error):
        self.insert_row(self.tables.errors, error)
