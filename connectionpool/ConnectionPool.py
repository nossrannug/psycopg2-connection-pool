from psycopg2.pool import PoolError
from psycopg2 import extensions as _ext
import threading
import time

class ConnectionPool():
    def __init__(
        self,
        maxconn: int,
        idle_time: int,
        original_pool,
        *args,
        # To use the same config object as is used for the original pool
        **kwargs,
    ):
        # Construct Semaphore with maxconn
        self.semaphore = threading.Semaphore(int(maxconn))
        self._org_pool = original_pool
        self._key = 0
        self._idle_pool = []
        self._last_used = {} # id(conn): time
        self._in_use_connections = {} # key: conn
        self._id_key_map = {} # id(conn): key
        self._lock = threading.Lock()
        # The daemon will run periodically and call putconn for all connections
        # that haven't been used for some amount of time
        self.daemon = threading.Thread(
            target=self.trim_pool,
            args=(idle_time,),
            daemon=True
        )
        self.daemon.start()

    def _get_next_key(self):
        self._key += 1
        return self._key

    def trim_pool(self, number_of_sec: int):
        while True and not self._org_pool.closed:
            # Yield the cpu to other threads for `number_of_sec` sec.
            # This is the least overhead but a connection might live for almost
            # 2 * number_of_sec sec
            time.sleep(number_of_sec)
            if self._org_pool.closed:
                # Stops the deamon if the pool has been closed
                break
            self._lock.acquire()
            try:
                # This only closes connections that have been idle for
                # `number_of_sec` sec
                t = time.time() - number_of_sec
                keep_conn = []
                close_conn = []
                for conn in self._idle_pool:
                    if self._last_used[id(conn)] > t:
                        keep_conn.append(conn)
                    else:
                        close_conn.append(conn)

                for conn in close_conn:
                    del self._last_used[id(conn)]
                    self._org_pool.putconn(conn)

                self._idle_pool = keep_conn
            finally:
                self._lock.release()

    def getconn(self, key=None):
        if self._org_pool.closed:
            raise PoolError("connection pool is closed")
        self.semaphore.acquire()
        self._lock.acquire()
        try:
            if not key:
                key = self._get_next_key()

            if key in self._in_use_connections:
                return self._in_use_connections[key]

            if self._idle_pool:
                # Get the oldest conn in the pool
                conn = self._idle_pool.pop(0)
            else:
                # If there is no connection in the pool then we open a new
                # connection
                print(key)
                conn = self._org_pool.getconn(key)

            self._id_key_map[id(conn)] = key
            self._in_use_connections[key] = conn

            return conn
        finally:
            self._lock.release()

    def putconn(self, conn, key=None, close=False):
        if self._org_pool.closed:
            raise PoolError("connection pool is closed")
        self._lock.acquire()
        try:
            if not key:
                key = self._id_key_map[id(conn)]
                if not key:
                    raise PoolError("trying to put unkeyed connection")

            if close:
                # Super will take care of all the clean up
                self._org_pool.putconn(conn, key, close)
                return

            # We need to handle all the clean up for the connection
            if not conn.closed:
                status = conn.info.transaction_status
                if status == _ext.TRANSACTION_STATUS_UNKNOWN:
                    # server connection lost
                    conn.close()
                elif status != _ext.TRANSACTION_STATUS_IDLE:
                    # connection in error or in transaction
                    conn.rollback()
                else:
                    # regular idle connection. Mark the time that we last used
                    # the connection before returning it to the pool
                    self._last_used[id(conn)] = time.time()
                    self._idle_pool.append(conn)

            if not self._org_pool.closed and key in self._in_use_connections:
                del self._in_use_connections[key]
                del self._id_key_map[id(conn)]
            
        finally:
            self._lock.release()
            self.semaphore.release()

    def closeall(self):
        self._org_pool.closeall()