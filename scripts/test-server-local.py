#!/usr/bin/env python3
"""
BundleCraft Local Test Server Script

Usage:
    test-server-local.py up [--port PORT] [--pem PEM] [--token TOKEN] [--verbose]
    test-server-local.py down [--verbose]
    test-server-local.py serve [--port PORT] [--pem PEM] [--token TOKEN] [--verbose]

Notes:
- Python-only: runs Flask HTTPS server with both HTTP and API endpoints
- Endpoints:
  - GET  /test-cert.pem (plain HTTP download)
  - POST /Certificates/Download (token-based API, Keyfactor-like)
- Self-signed cert/key stored in /tmp/test-server-local-<random>/
- Swagger UI available at /apidocs
"""
import os
import random
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path

import click

DEFAULT_PORT = 8443
DEFAULT_PEM = None
DEFAULT_TOKEN = "mock-token-12345"
PID_FILE_NAME = "server.pid"
TMP_PREFIX = "test-server-local-"


def log(msg):
    click.echo(click.style(f"[INFO] {msg}", fg="green"))


def warn(msg):
    click.echo(click.style(f"[WARN] {msg}", fg="yellow"), err=True)


def error(msg):
    click.echo(click.style(f"[ERROR] {msg}", fg="red"), err=True)
    sys.exit(1)


def random_dir():
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    path = Path(tempfile.gettempdir()) / f"{TMP_PREFIX}{rand}"
    # Write latest path for down command
    latest = Path(tempfile.gettempdir()) / f"{TMP_PREFIX}latest"
    latest.write_text(str(path), encoding="utf-8")
    return path


def get_python_executable() -> str:
    """
    Prefer the project's virtual environment Python if available; otherwise use the current interpreter.
    Fallback to 'python3' as last resort.
    """
    try:
        root = Path(__file__).resolve().parent.parent
        venv_py = root / "venv" / "bin" / "python"
        if venv_py.exists():
            return str(venv_py)
    except Exception:
        pass
    return sys.executable or "python3"


def make_tls_material(data_dir: Path, verbose: bool):
    crt = data_dir / "server.crt"
    key = data_dir / "server.key"
    if crt.exists() and key.exists():
        return crt, key
    data_dir.mkdir(parents=True, exist_ok=True)
    subj = "/CN=localhost"
    cmd = f'openssl req -x509 -newkey rsa:2048 -nodes -keyout "{key}" -out "{crt}" -days 2 -subj "{subj}" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"'
    subprocess.run(cmd, shell=True, check=True)
    return crt, key


def write_app_py(data_dir: Path, pem_path: Path, port: int):
    app_py = data_dir / "app.py"
    # Use a regular string and format at the end to avoid issues with curly braces
    code_template = """from flask import Flask, send_file, request, Response, render_template_string
from flasgger import Swagger
import os

app = Flask(__name__)
swagger = Swagger(app, template={{
    "info": {{
        "title": "BundleCraft Test Server!",
        "description": "If you can read this, your server is successfully running! Test endpoints: GET /test-cert.pem for plain HTTP download, POST /Certificates/Download for token-based API, and visit /apidocs for Swagger UI.",
        "version": "1.0.0"
    }},
    "host": "127.0.0.1:{port}",
    "basePath": "/"
}})

EXPECTED_TOKEN = os.environ.get('EXPECTED_TOKEN', '')
PEM_PATH = os.environ.get('PEM_PATH', '{pem_path}')

def _load_pem():
    if PEM_PATH and os.path.isfile(PEM_PATH):
        with open(PEM_PATH, 'r') as f:
            return f.read()
    return ''

@app.route('/')
def index():
  html = \"\"\"{{% raw %}}<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>BundleCraft Test Server home page!</title></head><body style='font-family:sans-serif;'><h1 style='color:#2b7a78;'>🛡️ BundleCraft Test Server home page! 🛡️</h1><p style='font-size:1.2em;'>Welcome to the <b>BundleCraft</b> local test server! 🚀<br>This server helps you test both <b>plain HTTP</b> and <b>token-based API</b> certificate downloads for your DevOps and CI/CD workflows.<br><span style='color:#3aafa9;'>Fast, friendly, and ephemeral!</span> ✨</p><hr><h2>Endpoints</h2><ul><li>🔓 <a href='/test-cert.pem'>GET /test-cert.pem</a> (plain HTTP download)</li><li>🔑 <b>POST</b> <code>/Certificates/Download</code> (token-based API, Keyfactor-like)</li><li>📖 <a href='/apidocs'>Swagger UI</a></li></ul><h3>Quick tests:</h3><p><b>HTTP download:</b></p><pre>curl -k https://127.0.0.1:{port}/test-cert.pem</pre><p><b>API download (with token):</b></p><pre>curl -k -X POST https://127.0.0.1:{port}/Certificates/Download \\n  -H 'Authorization: Bearer YOUR_TOKEN' \\n  -H 'Content-Type: application/json' \\n  -d '{{{{\"CertID\": 12345, \"CertificateFormat\": \"PEM\", \"IncludeChain\": true}}}}'</pre><hr><p style='color:#17252a;'>Made with ❤️ for DevOps, CI/CD, and PKI testing. <b>Spin up, test, and shut down in seconds!</b></p><p><a href='https://bundlecraft.io' target='_blank' style='color:#0077cc;font-weight:bold;'>Learn more about BundleCraft &rarr;</a></p></body></html>{{% endraw %}}\"\"\"
  return render_template_string(html)

@app.route('/test-cert.pem', methods=['GET'])
def serve_pem():
    '''
    Serve a test PEM file (plain HTTP download)
    ---
    tags:
      - HTTP Download
    produces:
      - application/x-pem-file
    responses:
      200:
        description: PEM file
        schema:
          type: string
      404:
        description: PEM not found
    '''
    if not PEM_PATH or not os.path.isfile(PEM_PATH):
        return Response('PEM not found', status=404)
    return send_file(PEM_PATH, mimetype='application/x-pem-file')

@app.route('/Certificates/Download', methods=['POST'])
def download():
    '''
    Download a certificate in PEM format (token-based API, Keyfactor-like)
    ---
    tags:
      - API Download
    consumes:
      - application/json
    produces:
      - application/x-pem-file
    parameters:
      - name: Authorization
        in: header
        required: true
        type: string
        description: Bearer access token (e.g., "Bearer abc123")
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            CertID:
              type: integer
              example: 12345
            CertificateFormat:
              type: string
              enum:
                - PEM
                - pem
              example: PEM
            IncludeChain:
              type: boolean
              example: true
    responses:
      200:
        description: Certificate data in PEM format
        schema:
          type: string
      400:
        description: Bad request (invalid or missing fields)
      401:
        description: Unauthorized (missing bearer token)
      403:
        description: Forbidden (token mismatch)
      404:
        description: PEM not available
    '''
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return Response('Unauthorized', status=401)
    token = auth.split(' ', 1)[1]
    if EXPECTED_TOKEN and token != EXPECTED_TOKEN:
        return Response('Forbidden', status=403)
    try:
        body = request.get_json(force=True, silent=False)
    except Exception:
        return Response('Bad Request: invalid JSON', status=400)
    # Basic validation similar to Keyfactor
    if not isinstance(body, dict):
        return Response('Bad Request', status=400)
    cert_id = body.get('CertID')
    fmt = body.get('CertificateFormat')
    include_chain = bool(body.get('IncludeChain', False))
    if cert_id is None or fmt not in ('PEM', 'pem'):
        return Response('Bad Request: missing/invalid fields', status=400)

    pem = _load_pem()
    if not pem:
        return Response('Not Found: no PEM available', status=404)
    # If IncludeChain, just return the same PEM twice for mock purposes
    payload = pem if not include_chain else (pem.strip() + '\\n' + pem.strip() + '\\n')
    return Response(payload, mimetype='application/x-pem-file')

if __name__ == '__main__':
    import ssl
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default={port})
    parser.add_argument('--crt', required=True)
    parser.add_argument('--key', required=True)
    args = parser.parse_args()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(args.crt, args.key)
    app.run(host='0.0.0.0', port=args.port, ssl_context=context)
"""
    code = code_template.format(port=port, pem_path=pem_path)
    app_py.write_text(code, encoding="utf-8")
    return app_py


def ensure_pem(data_dir: Path, pem: str):
    pem_path = data_dir / "test-cert.pem"
    if pem:
        src = Path(pem)
        if src.exists():
            shutil.copy(src, pem_path)
            return pem_path
    # Use server cert as default PEM
    pem_src = data_dir / "server.crt"
    if pem_src.exists():
        return pem_src
    # Fallback: default PEM content
    pem_content = """-----BEGIN CERTIFICATE-----
MIICxjCCAa6gAwIBAgIUTest123456789ABCDEFGHIJKLMN0wDQYJKoZIhvcNAQEL
BQAwDzENMAsGA1UEAwwEVEVTVDAeFw0yNTAxMDEwMDAwMDBaFw0zNTAxMDEwMDAw
MDBaMA8xDTALBgNVBAMMBFRFU1QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
AoIBAQDExampleCertDataHere123456789ABCDEFGHIJKLMNOP
-----END CERTIFICATE-----
"""
    pem_path.write_text(pem_content, encoding="utf-8")
    return pem_path


def get_pid_file(data_dir: Path):
    return data_dir / PID_FILE_NAME


@click.group()
def cli():
    pass


@cli.command()
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--pem", type=click.Path(), default=DEFAULT_PEM)
@click.option("--token", type=str, default=DEFAULT_TOKEN)
@click.option("--verbose", is_flag=True, default=False)
def up(port, pem, token, verbose):
    # Check if port is already in use
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            error(
                f"Port {port} is already in use. Choose a different port or stop the conflicting service."
            )

    data_dir = random_dir()
    log("Starting test server...")
    log(f"  Data dir: {data_dir}")
    log(f"  Port: {port}")
    log(f'  Expected token (masked): ****{token[-4:] if token else ""}')

    crt, key = make_tls_material(data_dir, verbose)
    pem_path = ensure_pem(data_dir, pem)
    app_py = write_app_py(data_dir, pem_path, port)
    pid_file = get_pid_file(data_dir)

    env = os.environ.copy()
    env["EXPECTED_TOKEN"] = token
    env["PEM_PATH"] = str(pem_path)

    log_file = data_dir / "flask.log"
    python_exec = get_python_executable()
    argv = [python_exec, str(app_py), "--port", str(port), "--crt", str(crt), "--key", str(key)]
    log(f'Starting Flask: {" ".join(argv)} > {log_file}')

    # Start Flask in a new process group for reliable shutdown
    lf = open(log_file, "w")
    p = subprocess.Popen(argv, env=env, stdout=lf, stderr=subprocess.STDOUT, preexec_fn=os.setsid)
    pid_file.write_text(str(p.pid))

    click.echo(f"\n✅ BundleCraft Test Server home page: https://127.0.0.1:{port}/")
    click.echo(f"- HTTP endpoint : https://127.0.0.1:{port}/test-cert.pem")
    click.echo(f"- API endpoint  : https://127.0.0.1:{port}/Certificates/Download")
    click.echo(f"- Swagger UI    : https://127.0.0.1:{port}/apidocs")
    click.echo(f"- CA file       : {crt}")
    click.echo(f"- Data dir      : {data_dir}")
    click.echo(f"- Log file      : {log_file}")
    click.echo(f'- Token (masked): ****{token[-4:] if token else ""}')
    click.echo("")
    click.echo("Quick tests:")
    click.echo(f"  HTTP: curl -k https://127.0.0.1:{port}/test-cert.pem")
    click.echo(f"  API:  curl -k -X POST https://127.0.0.1:{port}/Certificates/Download \\")
    click.echo(f'          -H "Authorization: Bearer {token}" \\')
    click.echo('          -H "Content-Type: application/json" \\')
    click.echo(
        '          -d \'{"CertID": 12345, "CertificateFormat": "PEM", "IncludeChain": true}\''
    )
    click.echo("")


@cli.command()
@click.option("--verbose", is_flag=True, default=False)
def down(verbose):
    # Use latest temp dir
    latest = Path(tempfile.gettempdir()) / f"{TMP_PREFIX}latest"
    if latest.exists():
        d = Path(latest.read_text(encoding="utf-8").strip())
        log("Tearing down test server...")
        pid_file = get_pid_file(d)
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            log(f"Killing PID {pid} and its process group...")
            import signal

            try:
                os.killpg(pid, signal.SIGKILL)
            except Exception as e:
                warn(f"Failed to kill process group: {e}")
            pid_file.unlink(missing_ok=True)
            shutil.rmtree(d, ignore_errors=True)
            log(f"Removed {d}")
        latest.unlink(missing_ok=True)
        log("Cleanup complete.")
    else:
        warn("No test server running.")


@cli.command()
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--pem", type=click.Path(), default=DEFAULT_PEM)
@click.option("--token", type=str, default=DEFAULT_TOKEN)
@click.option("--verbose", is_flag=True, default=False)
def serve(port, pem, token, verbose):
    # Check if port is already in use
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            error(
                f"Port {port} is already in use. Choose a different port or stop the conflicting service."
            )

    # Run Flask HTTPS server in foreground
    data_dir = random_dir()
    crt, key = make_tls_material(data_dir, verbose)
    pem_path = ensure_pem(data_dir, pem)
    app_py = write_app_py(data_dir, pem_path, port)

    env = os.environ.copy()
    env["EXPECTED_TOKEN"] = token
    env["PEM_PATH"] = str(pem_path)

    log(f"Running test server in foreground on port {port}...")
    python_exec = get_python_executable()
    os.execv(
        python_exec,
        [python_exec, str(app_py), "--port", str(port), "--crt", str(crt), "--key", str(key)],
    )


if __name__ == "__main__":
    cli()
