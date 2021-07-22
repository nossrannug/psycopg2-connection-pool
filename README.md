# Psycopg2 Connection pool
Improved connection pool for psycopg2

- This pool will not throw when trying to get a connection from the pool and
  there are none available. Instead it will wait for an available connection.
- When returning a connection to the pool it will not close it, even if there
  are `minconn` connections in the pool already. Instead it will keep track of
  when the connection was last used. A daemon will run periodically and close
  connections that have been idle for a set amount of time. This allows setting
  `minconn` to 0 and `maxconn` to 10. When there is heavy load there will be 10
  connections open. Once the load stops then the open database connections will
  be closed.
- It is thread safe

## To use this pool:
### Out of the box:
```python
from psycopg2.pool import SimpleConnectionPool
from connectionpool import ConnectionPool

config = {
  "minconn": 0,
  "maxconn": 10,
  ...
}

# This constructs a SimpleConnectionPool. ConnectionPool is thread safe
# so there is no need to use ThreadedConnectionPool
pool = ConnectionPool(
  idle_time=2 # time in sec
  **config,
)
```

### Custom pool:
```python
class MyCustomConnectionPool(SimpleConnectionPool): # Also works with Threaded
  ...

# If you have a custom connection pool that you would rather use that
# implements the same methods as the psycopg2 connection pools you can
# also use that with ConnectionPool
custom_pool = MyCustomConnectionPool(**config)
pool = ConnectionPool(
  idle_time=2,
  original_pool=custom_pool,
  # Then there is no need to pass in the config
)
```

### Methods:
The ConnectionPool class has the same function signatures as the
SimpleConnectionPool class

```python
# Get a connection:
conn = pool.getconn()
with conn.cursor() as cur:
    cur.execute(SQL, values)
    ...

# Put back a connection
pool.putconn(conn)

# Close all connections in the pool
pool.closeall()
```