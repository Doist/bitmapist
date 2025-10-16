import atexit
import os
import shutil
import socket
import subprocess
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from bitmapist import delete_all_events, get_redis, setup_redis

# Backend types
BACKEND_REDIS = "redis"
BACKEND_BITMAPIST_SERVER = "bitmapist-server"

# Safety threshold for existing keys
SAFE_EXISTING_KEY_THRESHOLD = 20


@dataclass
class BackendConfig:
    """Configuration for a backend server"""

    port_env: str
    default_port: int
    path_env: str
    binary_name: str
    fallback_path: str | None
    install_hint: str
    start_args: Callable[[int, Path], list[str]]


@dataclass
class BackendStatus:
    """Status of a backend server"""

    available: bool
    mode: str | None  # "docker", "native", or None
    port: int
    binary_path: str | None


# Single source of truth for backend configuration
BACKEND_CONFIGS = {
    BACKEND_REDIS: BackendConfig(
        port_env="BITMAPIST_REDIS_PORT",
        default_port=6399,
        path_env="BITMAPIST_REDIS_SERVER_PATH",
        binary_name="redis-server",
        fallback_path="/usr/bin/redis-server",
        install_hint="Install redis-server using your package manager",
        start_args=lambda port, temp_dir: [
            "--port",
            str(port),
            "--dir",
            str(temp_dir),
            "--dbfilename",
            "redis.rdb",
        ],
    ),
    BACKEND_BITMAPIST_SERVER: BackendConfig(
        port_env="BITMAPIST_SERVER_PORT",
        default_port=6400,
        path_env="BITMAPIST_SERVER_PATH",
        binary_name="bitmapist-server",
        fallback_path=None,
        install_hint="Download from https://github.com/Doist/bitmapist-server/releases",
        start_args=lambda port, temp_dir: [
            "-addr",
            f"0.0.0.0:{port}",
            "-db",
            str(temp_dir / "bitmapist.db"),
        ],
    ),
}


def is_socket_open(host, port):
    """Helper function which tests is the socket open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    return sock.connect_ex((host, port)) == 0


def get_backend_status(backend_config):
    """
    Check if a backend is available and how.

    Returns BackendStatus with:
    - available: bool
    - mode: "docker", "native", or None
    - port: int
    - binary_path: str or None
    """
    port = int(os.getenv(backend_config.port_env, str(backend_config.default_port)))

    # Check if already running (Docker or external)
    if is_socket_open("127.0.0.1", port):
        return BackendStatus(
            available=True,
            mode="docker",
            port=port,
            binary_path=None,
        )

    # Check for binary
    binary_path = os.getenv(backend_config.path_env)
    if not binary_path:
        binary_path = shutil.which(backend_config.binary_name)
    if not binary_path and backend_config.fallback_path:
        binary_path = backend_config.fallback_path

    if binary_path and Path(binary_path).exists():
        return BackendStatus(
            available=True,
            mode="native",
            port=port,
            binary_path=binary_path,
        )

    return BackendStatus(
        available=False,
        mode=None,
        port=port,
        binary_path=None,
    )


@pytest.fixture(scope="session")
def available_backends():
    """
    Check which backend servers are available on the system.
    Checks for running servers (Docker) OR available binaries.
    Fails the test suite if NO backends are available.
    """
    backends = []

    for backend_name, config in BACKEND_CONFIGS.items():
        status = get_backend_status(config)
        if status.available:
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
    default_path = shutil.which(config.binary_name)
    if not default_path and config.fallback_path:
        default_path = config.fallback_path
    server_path = os.getenv(config.path_env, default_path or "")
    port = int(os.getenv(config.port_env, str(config.default_port)))

    return {
        "server_path": server_path,
        "port": port,
        "backend_type": backend_type,
    }


@pytest.fixture(scope="session", autouse=True)
def backend_server(backend_settings, tmp_path_factory):
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
        temp_dir = tmp_path_factory.mktemp(f"{backend_type}-data")
        config = BACKEND_CONFIGS[backend_type]
        command = [server_path, *config.start_args(port, temp_dir)]
        proc = start_backend_server(command)
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
        f"  {config.install_hint}\n"
        f"  Ensure it's in your PATH\n\n"
        f"Option 3: Specify binary path\n"
        f"  export {config.path_env}=/path/to/{backend_type}\n\n"
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
    Fails if too many keys exist (likely production data).
    Warns if small number of keys from previous test runs.
    """
    cli = get_redis("default")
    existing_keys = cli.keys("trackist_*")

    if not existing_keys:
        return

    backend = f"{backend_settings['backend_type']}:{backend_settings['port']}"

    if len(existing_keys) > SAFE_EXISTING_KEY_THRESHOLD:
        pytest.fail(
            f"Found {len(existing_keys)} existing bitmapist keys in {backend}. "
            f"This exceeds safe threshold ({SAFE_EXISTING_KEY_THRESHOLD}). "
            f"Refusing to run tests to avoid data loss."
        )

    # Below threshold - just warn
    warnings.warn(
        f"Found {len(existing_keys)} existing keys in {backend} "
        f"(likely from previous test runs). These will be deleted during test cleanup.",
        UserWarning,
        stacklevel=2,
    )


@pytest.fixture(autouse=True)
def clean_redis():
    delete_all_events()


def pytest_report_header(config):
    """Add backend information to pytest header"""
    headers = []

    for backend_name, backend_config in BACKEND_CONFIGS.items():
        status = get_backend_status(backend_config)

        if status.mode == "docker":
            headers.append(
                f"{backend_name}: Docker/external server on port {status.port}"
            )
        elif status.mode == "native":
            headers.append(
                f"{backend_name}: Native binary ({status.binary_path}) on port {status.port}"
            )
        else:
            headers.append(f"{backend_name}: Not available")

    return headers


def start_backend_server(command):
    """Helper function starting backend server (Redis or bitmapist-server)"""
    devzero = open(os.devnull)
    devnull = open(os.devnull, "w")
    proc = subprocess.Popen(
        command,
        stdin=devzero,
        stdout=devnull,
        stderr=devnull,
        close_fds=True,
    )
    atexit.register(lambda: proc.terminate())
    return proc


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
