#!/usr/bin/env python3
"""
BundleCraft Local Vault Test Environment (Python Refactor)

Usage:
  vault-local.py up [--runtime binary|podman] [--port PORT] [--data-dir DIR] [--token TOKEN] [--image IMAGE] [--ci-cmd CMD] [--auto-cleanup] [--verbose]
  vault-local.py down [--runtime binary|podman] [--port PORT] [--data-dir DIR] [--token TOKEN] [--image IMAGE] [--verbose]

- If --runtime binary: use vault CLI for all interactions
- If --runtime podman: use only Vault API (via hvac)
- Full verbosity and step logging
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

import click
import hvac

DEFAULT_PORT = 8200
DEFAULT_DATA_DIR = os.path.abspath("./local_vault")
DEFAULT_TOKEN = "root"
DEFAULT_IMAGE = "hashicorp/vault:latest"
DEFAULT_RUNTIME = "binary"


def log(msg):
    click.echo(click.style(f"[INFO] {msg}", fg="green"))


def warn(msg):
    click.echo(click.style(f"[WARN] {msg}", fg="yellow"), err=True)


def error(msg):
    click.echo(click.style(f"[ERROR] {msg}", fg="red"), err=True)
    sys.exit(1)


def run(cmd, check=True, capture_output=False, env=None):
    log(f"Running: {cmd}")
    result = subprocess.run(
        cmd, shell=True, check=check, capture_output=capture_output, env=env, text=True
    )
    if capture_output:
        return result.stdout.strip()
    return None


def wait_for_vault(addr, token, timeout=15):
    log(f"Waiting for Vault at {addr} ...")
    client = hvac.Client(url=addr, token=token)
    for _ in range(timeout * 2):
        try:
            if client.sys.is_initialized() and client.sys.is_sealed() is False:
                log("Vault is ready.")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    error("Vault did not become ready in time.")


def start_vault_binary(port, data_dir, token, verbose):
    if shutil.which("vault") is None:
        error("Vault CLI not found. Install from https://developer.hashicorp.com/vault/downloads")
    os.makedirs(data_dir, exist_ok=True)
    pid_file = os.path.join(data_dir, "vault.pid")
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = int(f.read().strip())
        if (
            pid
            and shutil.which("ps")
            and subprocess.run(f"ps -p {pid}", shell=True).returncode == 0
        ):
            error(f"Vault already running (PID {pid}). Stop it first.")
    log("Starting Vault (binary mode)...")
    log(f"  Data dir: {data_dir}")
    log(f"  Port: {port}")
    log(f"  Token: {token}")
    logfile = os.path.join(data_dir, "vault.log")
    cmd = f'vault server -dev -dev-root-token-id={token} -dev-listen-address=127.0.0.1:{port} >"{logfile}" 2>&1 & echo $!'
    pid = run(cmd, capture_output=True)
    with open(pid_file, "w") as f:
        f.write(str(pid))
    time.sleep(2)
    log(f"Vault started with PID {pid}")
    return pid


def stop_vault_binary(data_dir):
    pid_file = os.path.join(data_dir, "vault.pid")
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = int(f.read().strip())
        log(f"Stopping Vault (PID {pid})...")
        subprocess.run(f"kill {pid}", shell=True)
        os.remove(pid_file)
    else:
        warn("No Vault process found to stop (binary mode).")
    shutil.rmtree(data_dir, ignore_errors=True)
    log("Cleanup complete.")


def start_vault_podman(port, data_dir, token, image, verbose):
    if shutil.which("podman") is None:
        error("Podman not found. Install from https://podman.io/getting-started")
    os.makedirs(data_dir, exist_ok=True)
    cname = "bundlecraft-vault"
    log("Starting Vault (Podman mode)...")
    log(f"  Data dir: {data_dir}")
    log(f"  Port: {port}")
    log(f"  Token: {token}")
    log(f"  Image: {image}")
    subprocess.run(
        f"podman rm -f {cname}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    cmd = f'podman run -d --name {cname} -p {port}:8200 -v "{data_dir}":/vault/data:Z -e VAULT_DEV_ROOT_TOKEN_ID={token} -e VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200 {image}'
    run(cmd)
    time.sleep(3)
    log("Vault Podman container started.")
    return cname


def stop_vault_podman(data_dir):
    cname = "bundlecraft-vault"
    log("Stopping Vault Podman container...")
    subprocess.run(f"podman rm -f {cname}", shell=True)
    shutil.rmtree(data_dir, ignore_errors=True)
    log("Cleanup complete.")


def configure_vault_binary(addr, token, verbose):
    log("Configuring Vault PKI test data (vault CLI)...")
    env = os.environ.copy()
    env["VAULT_ADDR"] = addr
    env["VAULT_TOKEN"] = token
    run("vault secrets enable -path=pki/trusted_roots pki", env=env)
    run("vault secrets tune -max-lease-ttl=8760h pki/trusted_roots", env=env)
    pem = run(
        "vault write -field=certificate pki/trusted_roots/root/generate/internal common_name=local-root-ca ttl=8760h",
        env=env,
        capture_output=True,
    )
    run(f'vault kv put secret/pki/trusted_roots pem="""{pem}"""', env=env)
    log("PEM written to Vault:")
    click.echo(pem.split("\n")[0:3])
    return pem


def configure_vault_api(addr, token, verbose):
    log("Configuring Vault PKI test data (API)...")
    client = hvac.Client(url=addr, token=token)
    # Enable PKI
    try:
        client.sys.enable_secrets_engine("pki", path="pki/trusted_roots")
    except Exception as e:
        warn(f"PKI engine may already be enabled: {e}")
    client.sys.tune_mount_configuration("pki/trusted_roots", max_lease_ttl="8760h")
    # Generate root CA
    try:
        resp = client.secrets.pki.generate_root(
            type="internal",
            common_name="local-root-ca",
            ttl="8760h",
            mount_point="pki/trusted_roots",
        )
        pem = resp["data"]["certificate"]
    except Exception as e:
        warn(f"PKI root generation failed: {e}")
        # Fallback: generate local PEM
        pem = None
    if not pem or not pem.startswith("-----BEGIN CERTIFICATE-----"):
        warn(
            "PKI engine did not return a valid certificate; generating a local test CA PEM instead."
        )
        tmpdir = tempfile.mkdtemp()
        crt = os.path.join(tmpdir, "root.crt")
        key = os.path.join(tmpdir, "root.key")
        run(
            f'openssl req -x509 -newkey rsa:2048 -nodes -keyout {key} -out {crt} -days 1 -subj "/CN=local-root-ca"'
        )
        with open(crt) as f:
            pem = f.read()
        shutil.rmtree(tmpdir)
    # Write to KV v2
    client.secrets.kv.v2.create_or_update_secret(
        path="pki/trusted_roots", secret={"pem": pem}, mount_point="secret"
    )
    log("PEM written to Vault:")
    click.echo("\n".join(pem.split("\n")[0:3]))
    return pem


def show_vault_info(addr, token, verbose):
    log("Vault info:")
    log(f"  Address: {addr}")
    log(f"  Token:   {token}")
    client = hvac.Client(url=addr, token=token)
    try:
        secret = client.secrets.kv.v2.read_secret_version(
            path="pki/trusted_roots", mount_point="secret"
        )
        pem = secret["data"]["data"]["pem"]
        log("PEM from Vault (first 3 lines):")
        click.echo("\n".join(pem.split("\n")[0:3]))
    except Exception as e:
        warn(f"Could not read PEM from Vault: {e}")


@click.group()
def cli():
    pass


@cli.command()
@click.option("--runtime", type=click.Choice(["binary", "podman"]), default=DEFAULT_RUNTIME)
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--data-dir", type=click.Path(), default=DEFAULT_DATA_DIR)
@click.option("--token", type=str, default=DEFAULT_TOKEN)
@click.option("--image", type=str, default=DEFAULT_IMAGE)
@click.option("--ci-cmd", type=str, default=None)
@click.option("--auto-cleanup", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
def up(runtime, port, data_dir, token, image, ci_cmd, auto_cleanup, verbose):
    addr = f"http://127.0.0.1:{port}"
    if runtime == "binary":
        start_vault_binary(port, data_dir, token, verbose)
        wait_for_vault(addr, token)
        configure_vault_binary(addr, token, verbose)
    else:
        start_vault_podman(port, data_dir, token, image, verbose)
        wait_for_vault(addr, token)
        configure_vault_api(addr, token, verbose)
    show_vault_info(addr, token, verbose)
    click.echo(f"\nVault Address : {addr}")
    click.echo(f"Root Token    : {token}")
    click.echo(f"Runtime       : {runtime}")
    if ci_cmd:
        log(f"Running CI command: {ci_cmd}")
        rc = os.system(ci_cmd)
        if rc != 0:
            warn(f"CI command failed with status {rc}")
        if auto_cleanup:
            cli.invoke(
                down,
                runtime=runtime,
                port=port,
                data_dir=data_dir,
                token=token,
                image=image,
                verbose=verbose,
            )
            sys.exit(rc)


@cli.command()
@click.option("--runtime", type=click.Choice(["binary", "podman"]), default=DEFAULT_RUNTIME)
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--data-dir", type=click.Path(), default=DEFAULT_DATA_DIR)
@click.option("--token", type=str, default=DEFAULT_TOKEN)
@click.option("--image", type=str, default=DEFAULT_IMAGE)
@click.option("--verbose", is_flag=True, default=False)
def down(runtime, port, data_dir, token, image, verbose):
    if runtime == "binary":
        stop_vault_binary(data_dir)
    else:
        stop_vault_podman(data_dir)


if __name__ == "__main__":
    cli()
