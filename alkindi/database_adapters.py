
import mysql.connector as mysql
from sqlbuilder.smartsql import Q, T, Query, Result
from sqlbuilder.smartsql.compilers.mysql import compile as mysql_compile
import json
from alkindi.errors import ModelError


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
        if isinstance(query, tuple):
            (stmt, values) = query
        elif isinstance(query, Query):
            (stmt, values) = mysql_compile(query)
        elif isinstance(query, str):
            stmt = query
            values = ()
        else:
            raise ModelError("invalid query type: {}".format(query))
        try:
            if self.log:
                print("[SQL] {};".format(stmt % tuple(values)))
            cursor = self.db.cursor()
            cursor.execute(stmt, values)
            return cursor
        except mysql.IntegrityError as ex:
            raise ModelError('integrity error', ex)
        except mysql.OperationalError as ex:
            raise ModelError('connection lost', ex)
        except (mysql.DataError,
                mysql.ProgrammingError,
                mysql.InternalError,
                mysql.NotSupportedError) as ex:
            raise ModelError('programming error', format(stmt))

    def scalar(self, query):
        cursor = self.execute(query.select())
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row is not None else None

    def count(self, query, **kwargs):
        cursor = self.execute(query.count(**kwargs))
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
        cursor = self.execute(query)
        row_id = cursor.lastrowid
        cursor.close()
        return None if row_id is None else row_id

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

    def row_scoped_query(self, table, value):
        """ If value is a scalar, add a (id=value) predicate to the query.
            If value is a dict, add the (table.column=value) predicates
            from the dict to the query.
        """
        query = self.query(table)
        if isinstance(value, dict):
            for col_name, col_value in value.items():
                query = query.where(getattr(table, col_name) == col_value)
        else:
            query = query.where(table.id == value)
        return query

    def rows_scoped_query(self, table, values):
        """ Add a (id in values) predicate to the query.
        """
        return self.query(table).where(table.id.in_(list(values)))

    def load_scalar(self, table, value, column):
        """ Load the specified `column` from the first row in `table`
            where `by`=`value`.
        """
        query = self.row_scoped_query(table, value)
        row = self.first(query.fields(getattr(table, column)))
        return None if row is None else row[0]

    def load_row(self, table, value, columns, for_update=False):
        query = self.row_scoped_query(table, value)
        query = query.fields(*[getattr(table, col) for col in columns])
        row = self.first(query, for_update=for_update)
        if row is None:
            raise ModelError('no such row')
        return {key: row[i] for i, key in enumerate(columns)}

    def load_rows(self, table, values, columns, for_update=False):
        if len(values) == 0:
            return []
        query = self.rows_scoped_query(table, values)
        query = query.fields(*[getattr(table, col) for col in columns])
        return [
            {key: row[i] for i, key in enumerate(columns)}
            for row in self.all(query, for_update=for_update)
        ]

    def insert_row(self, table, attrs):
        query = self.query(table)
        query = query.insert(
            {getattr(table, key): attrs[key] for key in attrs})
        return self.insert(query)

    def update_row(self, table, value, attrs):
        query = self.row_scoped_query(table, value)
        return self.update(
            query, {getattr(table, key): attrs[key] for key in attrs})

    def first_row(self, query, cols):
        rows = self.all_rows(query[:1], cols)
        if len(rows) == 0:
            return None
        row = rows[0]
        self.decode_row(row, cols)
        return row

    def all_rows(self, query, cols):
        query = query.fields([col[1] for col in cols])
        rows = [{col[0]: row[i] for i, col in enumerate(cols)}
                for row in self.all(query)]
        self.decode_rows(rows, cols)
        return rows

    def decode_rows(self, rows, cols):
        for row in rows:
            self.decode_row(row, cols)

    def decode_row(self, row, cols):
        for col in cols:
            key = col[0]
            if len(col) == 3:
                if col[2] == 'bool':
                    row[key] = self.load_bool(row[key])
                elif col[2] == 'json':
                    row[key] = self.load_json(row[key])

    def log_error(self, error):
        self.insert_row(self.tables.errors, error)
