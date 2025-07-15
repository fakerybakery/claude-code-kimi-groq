import os
import sys
import signal
import subprocess
import time
import json
import platform
import random
import socket
from pathlib import Path
from cryptography.fernet import Fernet

import click
import keyring
import psutil
import uvicorn
from rich.console import Console
from rich.panel import Panel

from .proxy import app

console = Console()

PROCESS_NAME = "cckimi-server"
PID_FILE = Path.home() / ".cckimi" / "server.pid"
PORT_FILE = Path.home() / ".cckimi" / "server.port"
CONFIG_DIR = Path.home() / ".cckimi"
CACHE_DIR = Path.home() / ".cache" / "cckimi"
KEY_FILE = CACHE_DIR / "key.enc"
SECRET_FILE = CACHE_DIR / "secret.key"

# Port range for random selection (avoiding common ports)
PORT_RANGE = list(range(18000, 19000)) + list(range(28000, 29000)) + list(range(38000, 39000))


def ensure_config_dir():
    """Ensure the config directory exists"""
    CONFIG_DIR.mkdir(exist_ok=True)


def ensure_cache_dir():
    """Ensure the cache directory exists"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_key():
    """Get or create encryption key for fallback storage"""
    ensure_cache_dir()
    if SECRET_FILE.exists():
        with open(SECRET_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(SECRET_FILE, 'wb') as f:
            f.write(key)
        # Set restrictive permissions
        SECRET_FILE.chmod(0o600)
        return key


def store_api_key_fallback(api_key):
    """Store API key in encrypted file as fallback"""
    try:
        key = get_or_create_key()
        f = Fernet(key)
        encrypted_key = f.encrypt(api_key.encode())
        
        with open(KEY_FILE, 'wb') as file:
            file.write(encrypted_key)
        
        # Set restrictive permissions
        KEY_FILE.chmod(0o600)
        return True
    except Exception as e:
        console.print(f"❌ Failed to store API key in fallback: {e}", style="red")
        return False


def get_api_key_fallback():
    """Get API key from encrypted file fallback"""
    try:
        if not KEY_FILE.exists():
            return None
        
        key = get_or_create_key()
        f = Fernet(key)
        
        with open(KEY_FILE, 'rb') as file:
            encrypted_key = file.read()
        
        decrypted_key = f.decrypt(encrypted_key)
        return decrypted_key.decode()
    except Exception:
        return None


def store_api_key(api_key):
    """Store API key using keyring with fallback"""
    try:
        keyring.set_password("cckimi", "groq_api_key", api_key)
        return True
    except Exception:
        console.print("⚠️  Keyring not available, using encrypted file fallback", style="yellow")
        return store_api_key_fallback(api_key)


def get_api_key():
    """Get API key using keyring with fallback"""
    try:
        key = keyring.get_password("cckimi", "groq_api_key")
        if key:
            return key
    except Exception:
        pass
    
    # Try fallback
    return get_api_key_fallback()


def remove_api_key():
    """Remove API key from both keyring and fallback"""
    try:
        keyring.delete_password("cckimi", "groq_api_key")
    except Exception:
        pass
    
    # Remove fallback files
    try:
        if KEY_FILE.exists():
            KEY_FILE.unlink()
        if SECRET_FILE.exists():
            SECRET_FILE.unlink()
    except Exception:
        pass


def is_port_available(port):
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('localhost', port))
            return True
    except socket.error:
        return False


def find_available_port():
    """Find an available port from the port range"""
    # Shuffle the port range for randomness
    ports = PORT_RANGE.copy()
    random.shuffle(ports)
    
    for port in ports:
        if is_port_available(port):
            return port
    
    # If no port in range is available, try a few more random ones
    for _ in range(10):
        port = random.randint(10000, 65535)
        if is_port_available(port):
            return port
    
    # Fallback to original port
    return 7187


def save_server_port(port):
    """Save the server port to file"""
    ensure_config_dir()
    with open(PORT_FILE, 'w') as f:
        f.write(str(port))


def get_server_port():
    """Get the server port from file"""
    if PORT_FILE.exists():
        try:
            with open(PORT_FILE, 'r') as f:
                return int(f.read().strip())
        except (ValueError, FileNotFoundError):
            pass
    return None


def remove_port_file():
    """Remove the port file"""
    if PORT_FILE.exists():
        PORT_FILE.unlink()


def get_server_pid():
    """Get the server PID from file"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
        except (ValueError, FileNotFoundError):
            return None
    return None


def save_server_pid(pid):
    """Save the server PID to file"""
    ensure_config_dir()
    with open(PID_FILE, 'w') as f:
        f.write(str(pid))


def remove_pid_file():
    """Remove the PID file"""
    if PID_FILE.exists():
        PID_FILE.unlink()


def is_server_running():
    """Check if the server is running"""
    pid = get_server_pid()
    if pid is None:
        return False
    
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except psutil.NoSuchProcess:
        remove_pid_file()
        return False


def start_server():
    """Start the server in the background"""
    if is_server_running():
        port = get_server_port()
        console.print(f"✅ Server is already running on port {port}", style="green")
        return
    
    # Get the Groq API key
    groq_key = get_api_key()
    if not groq_key:
        console.print("❌ No Groq API key found. Please run 'cckimi login' first.", style="red")
        return
    
    # Find an available port
    port = find_available_port()
    
    # Start server in background
    env = os.environ.copy()
    env["GROQ_API_KEY"] = groq_key
    
    # Windows-specific process creation
    if platform.system() == "Windows":
        # Use CREATE_NEW_PROCESS_GROUP instead of start_new_session on Windows
        process = subprocess.Popen(
            [sys.executable, "-c", f"from cckimi.proxy import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port={port})"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        process = subprocess.Popen(
            [sys.executable, "-c", f"from cckimi.proxy import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port={port})"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    
    save_server_pid(process.pid)
    save_server_port(port)
    
    # Wait a moment and check if it started successfully
    time.sleep(2)
    if is_server_running():
        console.print(f"✅ Server started successfully on port {port}", style="green")
    else:
        console.print("❌ Failed to start server", style="red")


def stop_server():
    """Stop the server"""
    pid = get_server_pid()
    if pid is None:
        console.print("❌ No server PID found", style="red")
        return
    
    try:
        process = psutil.Process(pid)
        
        # Windows-specific termination
        if platform.system() == "Windows":
            # On Windows, use CTRL_BREAK_EVENT for graceful shutdown
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            except AttributeError:
                # Fallback to terminate if signal not available
                process.terminate()
        else:
            process.terminate()
        
        process.wait(timeout=5)
        remove_pid_file()
        remove_port_file()
        console.print("✅ Server stopped successfully", style="green")
    except psutil.NoSuchProcess:
        remove_pid_file()
        console.print("❌ Server process not found", style="red")
    except psutil.TimeoutExpired:
        try:
            process.kill()
            remove_pid_file()
            remove_port_file()
            console.print("✅ Server killed successfully", style="green")
        except psutil.NoSuchProcess:
            remove_pid_file()
            remove_port_file()
            console.print("❌ Server process not found", style="red")


def get_server_status():
    """Get the server status"""
    if is_server_running():
        pid = get_server_pid()
        port = get_server_port()
        return f"✅ Server is running (PID: {pid}, Port: {port})"
    else:
        return "❌ Server is not running"


@click.group()
def cckimi_cli():
    """Claude Code Kimi-Groq Proxy CLI"""
    pass


@cckimi_cli.command()
def start():
    """Start the proxy server"""
    start_server()


@cckimi_cli.command()
def stop():
    """Stop the proxy server"""
    stop_server()


@cckimi_cli.command()
def status():
    """Check server status"""
    status = get_server_status()
    console.print(status)


@cckimi_cli.command()
def login():
    """Store Groq API key"""
    groq_key = click.prompt("Enter your Groq API key", hide_input=True)
    if store_api_key(groq_key):
        console.print("✅ Groq API key stored successfully", style="green")
    else:
        console.print("❌ Failed to store Groq API key", style="red")


@cckimi_cli.command()
def logout():
    """Remove stored Groq API key"""
    if get_api_key():
        remove_api_key()
        console.print("✅ Groq API key removed successfully", style="green")
    else:
        console.print("❌ No API key found to remove", style="yellow")


@click.command()
@click.pass_context
def kimi_cli(ctx):
    """Run claude with Kimi-Groq proxy"""
    # Force login if no API key is found
    if not get_api_key():
        console.print("❌ No Groq API key found. Please login first.", style="red")
        if click.confirm("Would you like to login now?"):
            groq_key = click.prompt("Enter your Groq API key", hide_input=True)
            if not store_api_key(groq_key):
                console.print("❌ Failed to store API key", style="red")
                sys.exit(1)
            console.print("✅ API key stored successfully", style="green")
        else:
            console.print("Please run 'cckimi login' to set up your API key", style="yellow")
            sys.exit(1)
    
    # Check if server is running, start if not
    if not is_server_running():
        console.print("🚀 Starting server...", style="yellow")
        start_server()
        if not is_server_running():
            console.print("❌ Failed to start server", style="red")
            sys.exit(1)
    
    # Set the base URL and run claude with all arguments
    port = get_server_port()
    if not port:
        console.print("❌ Could not determine server port", style="red")
        sys.exit(1)
    
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = f"http://localhost:{port}"
    env["ANTHROPIC_API_KEY"] = "NOT_NEEDED"
    
    # Get all arguments passed to kimi and pass them to claude
    args = sys.argv[1:]
    cmd = ["claude"] + args
    
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        console.print("❌ Claude CLI not found. Please install it first.", style="red")
        sys.exit(1)


if __name__ == "__main__":
    cckimi_cli()