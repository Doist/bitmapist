import atexit
import os
import shutil
import socket
import subprocess
import time
import warnings
from pathlib import Path

import pytest

from bitmapist import delete_all_events, get_redis, setup_redis

# Backend types
BACKEND_REDIS = "redis"
BACKEND_BITMAPIST_SERVER = "bitmapist-server"

# Single source of truth for backend configuration
BACKEND_CONFIGS = {
    BACKEND_REDIS: {
        "port_env": "BITMAPIST_REDIS_PORT",
        "default_port": 6399,
        "path_env": "BITMAPIST_REDIS_SERVER_PATH",
        "binary_name": "redis-server",
        "fallback_path": "/usr/bin/redis-server",
        "install_hint": "Install redis-server using your package manager",
        "start_args": lambda port: ["--port", str(port)],
    },
    BACKEND_BITMAPIST_SERVER: {
        "port_env": "BITMAPIST_SERVER_PORT",
        "default_port": 6400,
        "path_env": "BITMAPIST_SERVER_PATH",
        "binary_name": "bitmapist-server",
        "fallback_path": None,
        "install_hint": "Download from https://github.com/Doist/bitmapist-server/releases",
        "start_args": lambda port: ["-addr", f"0.0.0.0:{port}"],
    },
}


def is_socket_open(host, port):
    """Helper function which tests is the socket open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def available_backends():
    """
    Check which backend servers are available on the system.
    Checks for running servers (Docker) OR available binaries.
    Fails the test suite if NO backends are available.
    """
    backends = []

    for backend_name, config in BACKEND_CONFIGS.items():
        port = int(os.getenv(config["port_env"], str(config["default_port"])))

        # Check if server is already running (Docker or external)
        if is_socket_open("127.0.0.1", port):
            backends.append(backend_name)
            continue

        # Check if binary is available
        path_str = os.getenv(config["path_env"])
        if path_str and Path(path_str).exists():
            backends.append(backend_name)
            continue

        # Check for binary in PATH or fallback location
        if shutil.which(config["binary_name"]):
            backends.append(backend_name)
            continue

        if config["fallback_path"] and Path(config["fallback_path"]).exists():
            backends.append(backend_name)

    if not backends:
        pytest.fail(
            "No backend servers available. Please install redis-server or bitmapist-server.\n"
            "Or set BITMAPIST_REDIS_SERVER_PATH or BITMAPIST_SERVER_PATH environment variables."
        )

    return backends


@pytest.fixture(params=[BACKEND_REDIS, BACKEND_BITMAPIST_SERVER], scope="session")
def backend_type(request):
    """
    Parametrized fixture that will cause the entire test suite to run twice:
    once with Redis, once with bitmapist-server.
    """
    return request.param


@pytest.fixture(scope="session")
def backend_settings(backend_type, available_backends):
    """
    Provides backend-specific configuration.
    Skips tests if the requested backend is not available.

    Uses environment variables to locate binaries:
    - BITMAPIST_REDIS_SERVER_PATH: Custom path to redis-server
    - BITMAPIST_SERVER_PATH: Custom path to bitmapist-server
    - BITMAPIST_REDIS_PORT: Custom port for Redis (default: 6399)
    - BITMAPIST_SERVER_PORT: Custom port for bitmapist-server (default: 6400)
    """
    # Skip if this backend is not available
    if backend_type not in available_backends:
        pytest.skip(f"{backend_type} not available on this system")

    config = BACKEND_CONFIGS[backend_type]

    # Try env var first, then auto-detect
    default_path = shutil.which(config["binary_name"])
    if not default_path and config["fallback_path"]:
        default_path = config["fallback_path"]
    server_path = os.getenv(config["path_env"], default_path or "")
    port = int(os.getenv(config["port_env"], str(config["default_port"])))

    return {
        "server_path": server_path,
        "port": port,
        "backend_type": backend_type,
    }


@pytest.fixture(scope="session", autouse=True)
def backend_server(backend_settings):
    """
    Smart backend server management with auto-detection.

    1. Check if server already running on the port → Use it (Docker/external)
    2. Try to find and start binary → Start it (managed mode)
    3. Nothing available → Fail with helpful error
    """
    host = "127.0.0.1"
    port = backend_settings["port"]
    backend_type = backend_settings["backend_type"]

    # Step 1: Check if already running (Docker or external process)
    if is_socket_open(host, port):
        yield None
        return

    # Step 2: Try to find and start binary
    server_path = backend_settings.get("server_path")
    if server_path and Path(server_path).exists():
        # Binary found, start it
        proc = start_backend_server(server_path, port, backend_type)
        wait_for_socket(host, port)
        yield proc
        proc.terminate()
        return

    # Step 3: Nothing available - provide helpful error
    config = BACKEND_CONFIGS[backend_type]
    pytest.fail(
        f"{backend_type} not available.\n\n"
        f"Option 1 (Recommended): Start with Docker\n"
        f"  docker compose up -d\n\n"
        f"Option 2: Install {backend_type} binary\n"
        f"  {config['install_hint']}\n"
        f"  Ensure it's in your PATH\n\n"
        f"Option 3: Specify binary path\n"
        f"  export {config['path_env']}=/path/to/{backend_type}\n\n"
        f"  pytest"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_redis_for_bitmapist(backend_settings):
    """Setup Redis connection for current backend"""
    port = backend_settings["port"]

    setup_redis("default", "localhost", port)
    setup_redis("default_copy", "localhost", port)
    setup_redis("db1", "localhost", port, db=1)


@pytest.fixture(scope="session", autouse=True)
def check_existing_data(backend_settings, setup_redis_for_bitmapist):
    """
    Check for existing data at session start.
    Warns if data exists but doesn't delete it (safety first).
    """
    cli = get_redis("default")
    existing_keys = cli.keys("trackist_*")

    if existing_keys:
        warnings.warn(
            f"\n{'=' * 70}\n"
            f"WARNING: Found {len(existing_keys)} existing bitmapist keys in backend.\n"
            f"Backend: {backend_settings['backend_type']} on port {backend_settings['port']}\n"
            f"\n"
            f"This may indicate:\n"
            f"1. Docker containers with data from previous runs\n"
            f"2. Shared backend being used by multiple projects\n"
            f"3. Production data in the backend (DANGER!)\n"
            f"\n"
            f"Tests will continue but results may be affected by existing data.\n"
            f"\n"
            f"To clean: docker compose down -v (removes volumes), or manually FLUSHDB.\n"
            f"{'=' * 70}\n",
            UserWarning,
            stacklevel=2,
        )


@pytest.fixture(autouse=True)
def clean_redis():
    delete_all_events()


def start_backend_server(server_path, port, backend_type):
    """Helper function starting backend server (Redis or bitmapist-server)"""
    devzero = open(os.devnull)
    devnull = open(os.devnull, "w")
    command = get_backend_command(server_path, port, backend_type)
    proc = subprocess.Popen(
        command,
        stdin=devzero,
        stdout=devnull,
        stderr=devnull,
        close_fds=True,
    )
    atexit.register(lambda: proc.terminate())
    return proc


def get_backend_command(server_path, port, backend_type):
    """
    Build the command to start the backend server.
    No need to detect which server type - we already know from backend_type.
    """
    config = BACKEND_CONFIGS[backend_type]
    return [server_path, *config["start_args"](port)]


def wait_for_socket(host, port, seconds=10):
    """Check if socket is up for :param:`seconds` sec, raise an error otherwise"""
    polling_interval = 0.1
    iterations = int(seconds / polling_interval)

    for _ in range(iterations):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return
        time.sleep(polling_interval)

    raise RuntimeError(f"Service at {host}:{port} is unreachable")
