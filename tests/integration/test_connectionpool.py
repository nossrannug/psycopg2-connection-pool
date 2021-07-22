import pytest
import time
from connectionpool import ConnectionPool

idle_time = .1
maxconn = 2

config = {
    "minconn": 0,
    "maxconn": maxconn,
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "pass",
    "database": "postgres",
}

@pytest.fixture
def pool():
    pool = ConnectionPool(idle_time=idle_time, **config)
    yield pool
    pool.closeall()

def test_connection_not_closed(pool):
    conn = pool.getconn()
    pool.putconn(conn)
    assert len(pool._idle_pool) == 1

def test_connection_closed_after_idle(pool):
    conn = pool.getconn()
    pool.putconn(conn)
    # Need to sleep long enough to make sure that the daemon cleans up the
    # connection
    time.sleep(idle_time * 3)
    assert len(pool._idle_pool) == 0

def test_connection_is_reused(pool):
    conn1 = pool.getconn()
    pool.putconn(conn1)
    conn2 = pool.getconn()
    assert id(conn1) == id(conn2)

def get_from_pool(pool):
    conn = pool.getconn()
    time.sleep(idle_time)
    pool.putconn(conn)

def test_wait_for_connection(pool):
    # No exception is thrown even though we try to get more connections than
    # there are available in the pool.
    import threading
    jobs = [
        threading.Thread(
            target=get_from_pool,
            args=(pool,),
        )
        for _ in range(maxconn * 2)
    ]
    for job in jobs:
        job.start()

    for job in jobs:
        job.join()


