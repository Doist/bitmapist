import pytest
import os
import subprocess
import atexit
import socket
import time


@pytest.yield_fixture(scope='session', autouse=True)
def redis_server():
    """
    Fixture starting the Redis server
    """
    redis_host = '127.0.0.1'
    redis_port = 6399
    if is_socket_open(redis_host, redis_port):
        yield None
    else:
        proc = start_redis_server(redis_port)
        wait_for_socket(redis_host, redis_port)
        yield proc
        proc.terminate()


def start_redis_server(port):
    """
    Helper function starting Redis server
    """
    devzero = open(os.devnull, 'r')
    devnull = open(os.devnull, 'w')
    proc = subprocess.Popen(['/usr/bin/redis-server', '--port', str(port)],
                            stdin=devzero, stdout=devnull, stderr=devnull,
                            close_fds=True)
    atexit.register(lambda: proc.terminate())
    return proc


def is_socket_open(host, port):
    """
    Helper function which tests is the socket open
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    return sock.connect_ex((host, port)) == 0


def wait_for_socket(host, port, seconds=3):
    """
    Check if socket is up for :param:`seconds` sec, raise an error otherwise
    """
    polling_interval = 0.1
    iterations = int(seconds / polling_interval)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    for _ in xrange(iterations):
        result = sock.connect_ex((host, port))
        if result == 0:
            sock.close()
            break
        time.sleep(polling_interval)
    else:
        raise RuntimeError('Service at %s:%d is unreachable' % (host, port))
