# 🏛️ PKI-CA-Trust

**PKI-CA-Trust** is a modular, automation-friendly framework for building and maintaining enterprise trust stores — reproducibly, safely, and across multiple environments.

It solves one of the least glamorous but most painful problems in large-scale PKI operations: **managing trusted CA certificates** consistently across systems, networks, and teams.

---

## 🌍 Why This Exists

In most organizations, “trust” is scattered across dozens of services:
- Web servers, load balancers, middleware, proxies
- Java, .NET, and OS-level certificate stores
- Air-gapped, cloud, and DMZ environments

Manually syncing these trusted roots and intermediates is **error-prone**, **non-auditable**, and **insecure**.

**PKI-CA-Trust** brings order to that chaos by treating trust management as **code** — configuration-driven, version-controlled, and fully automatable.

---

## ⚙️ Core Features

| Capability | Description |
|-------------|-------------|
| 🧩 **Three-layer design** | Configuration separated into defaults, environments, and bundles |
| 🧰 **Automated build system** | Generates canonical PEM, JKS, P7B, and DER bundles |
| 🕵️ **Verification built-in** | Detects expired and soon-to-expire certs |
| 🔐 **Fail-closed by default** | Any untrustworthy or expired certificate aborts the build |
| 🧾 **Manifest & checksums** | Every bundle has reproducible metadata and SHA-256 integrity records |
| 📦 **Distributable artifacts** | Optional `.tar.gz` packaging for publication to file shares, Artifactory, or containers |
| 🧪 **Standalone verifier** | Validate any PEM bundle with a single command |
| 🧠 **Human-readable PEMs** | Adds `# Subject:` lines above each cert for traceability |
| ⚡ **Simple, familiar tech** | Written in Python, with JSON/YAML configs and Click CLI |

---

## 🚀 Quick Start

### 1️⃣ Create and activate a virtual environment
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
### 2️⃣ Build your trust bundle
```
python scripts/build_trust_store.py --env prod --bundle internal --package
```
### 3️⃣ Verify trust integrity only
```
python scripts/build_trust_store.py --env prod --bundle internal --verify-only
```
Artifacts appear under:
```
build/prod/internal/
```
---

## 📘 Documentation

|              Document             	|             Description             	|
|:---------------------------------:	|:-----------------------------------:	|
| docs/02-architecture.md           	| System architecture                 	|
| docs/03-directory-structure.md    	| Folder layout                       	|
| docs/04-config-design.md          	| Configuration model and YAML schema 	|
| docs/05-scripts-and-components.md 	| Script roles and interactions       	|
| docs/06-checksums.md              	| Checksum verification guide         	|
| docs/07-verifier.md               	| Verifier usage and output           	|
| docs/08-cli-reference.md          	| CLI flags, usage, and exit codes    	|

## 🧩 Example Use Case

“We need to distribute a single unified trust store for all internal services, including Java apps, NGINX proxies, and Linux hosts.”

**PKI-CA-Trust:**
- Pulls all authorized CA certs from version-controlled sources/
- Validates expiration and deduplicates them
- Builds .pem, .jks, and .p7b bundles automatically
- Packages them for delivery to any target system
---
## 🔒 Design Philosophy
- Reproducibility: Every build produces identical, auditable outputs.
- Transparency: All configs and trust changes live in Git.
- Fail-safe: Untrusted input halts the build instead of being silently ignored.
- Simplicity: Minimal dependencies, straightforward YAML and Python.
---
## 💡 Ideal for
- PKI and Security Engineering teams
- DevOps automation pipelines
- Regulated environments needing deterministic trust distribution
- Hybrid orgs managing multiple OS / language stacks
---
## 🧑‍💻 Contributing
This project is early in design and welcomes structured feedback, PRs, and configuration templates.
Please follow standard Git workflow conventions and open pull requests for discussion.
---
⚖️ License

MIT License © 2025 — See `LICENSE` for details.