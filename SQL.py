import sqlite3
import threading
import logging

class SQLiteHelper:
    """
    SQLiteHelper: A thread-safe helper class for SQLite database interactions.
    """
    def __init__(self, db_path='users.db', timeout=5.0,
                 check_same_thread=False, isolation_level=None):
        """
        Initialize the SQLiteHelper.
        - db_path: Path to the SQLite .db file (':memory:' for in-memory).
        - timeout: max seconds to wait for lock.
        - check_same_thread=False allows multi-thread use (with external locking).
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        # Open connection (serialized by default); allow access from any thread
        self.conn = sqlite3.connect(db_path, timeout=timeout,
                                    check_same_thread=check_same_thread,
                                    isolation_level=isolation_level)
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Commit or rollback on exit, then close
        try:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            try:
                self.cursor.close()
            except Exception:
                pass
            try:
                self.conn.close()
            except Exception:
                pass

    def close(self):
        """Manually close cursor and connection."""
        try:
            self.cursor.close()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass

    def execute(self, sql, params=None, fetchone=False, fetchall=False, fetchmany=None, commit=True):
        """
        Execute a SQL statement with optional parameters and fetch mode.
        - Sql (str): the SQL query or command.
        - params (tuple or dict): parameters for placeholders.
        - fetchone/fetchall (bool): if True, return one/all rows.
        - fetchmany (int): if not None, fetch up to this many rows.
        - commit (bool): whether to commit after execution.

        Returns:
          - If fetchone=True: a single row tuple or None.
          - If fetchall=True: a list of row tuples.
          - If fetchmany=n: a list of up to n rows.
          - Otherwise: None (useful for INSERT/UPDATE).
        """
        with self._lock:
            try:
                if params is None:
                    cur = self.cursor.execute(sql)
                else:
                    cur = self.cursor.execute(sql, params)
                self.logger.debug(f"Executed SQL: {sql!r} | params: {params!r}")
                if fetchone:
                    result = cur.fetchone()
                elif fetchall:
                    result = cur.fetchall()
                elif fetchmany is not None:
                    result = cur.fetchmany(fetchmany)
                else:
                    result = None
                if commit:
                    self.conn.commit()
                return result
            except Exception as e:
                self.conn.rollback()
                self.logger.exception(f"SQL error: {sql!r} | params: {params!r}")
                raise

    def executemany(self, sql, seq_of_params, commit=True):
        """
        Execute the same SQL with a sequence of parameter sets.
        """
        with self._lock:
            try:
                cur = self.cursor.executemany(sql, seq_of_params)
                self.logger.debug(f"Executed SQL (many): {sql!r} | params: {seq_of_params!r}")
                if commit:
                    self.conn.commit()
                return cur
            except Exception as e:
                self.conn.rollback()
                self.logger.exception(f"SQL executemany error: {sql!r} | params: {seq_of_params!r}")
                raise

    def count(self, table, where=None, params=None):
        """
        Return COUNT(*) from the given table, with optional WHERE clause.
        """
        sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            sql += " WHERE " + where
        row = self.execute(sql, params, fetchone=True)
        return row[0] if row else 0

    def insert(self, table, data):
        """
        Insert a row into the table.
        - data: dict mapping column names to values.
        Returns the new row's ID.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self.execute(sql, tuple(data.values()), commit=True)
        return self.cursor.lastrowid

    def update(self, table, data, where, where_params=None):
        """
        Update rows in `table`.
        - data: dict of columns to new values.
        - where: SQL WHERE clause (no 'WHERE' keyword).
        - where_params: parameters for the WHERE clause.
        Returns number of rows updated.
        """
        set_clause = ", ".join(f"{col}=?" for col in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values())
        if where_params:
            params += list(where_params)
        self.execute(sql, tuple(params), commit=True)
        return self.cursor.rowcount

    def fetchall(self, sql, params=None):
        """Shortcut: execute query and return all rows."""
        return self.execute(sql, params, fetchall=True)

    def fetchone(self, sql, params=None):
        """Shortcut: execute query and return one row."""
        return self.execute(sql, params, fetchone=True)

    def __del__(self):
        # Ensure connection is closed upon garbage collection
        try:
            self.close()
        except Exception:
            pass
