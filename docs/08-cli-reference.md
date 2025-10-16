## 🧰 2. `docs/09-cli-reference.md`

# CLI Reference

The main interface is a single Click-based command:

```bash
python scripts/builder.py [OPTIONS]
```
```
Option	Description
--env TEXT	Environment name (required)
--bundle TEXT	Bundle name (required)
--package	Also create .tar.gz package
--verify-only	Only verify certificates; skip build
-h, --help	Show help and exit
```

## Examples
Build and package
```bash
python scripts/builder.py --env prod --bundle internal --package
```
Verify bundle only
```bash
python scripts/builder.py --env prod --bundle internal --verify-only
```
## Exit Codes
```
Code	Meaning
0	Success
2	No sources found
3	No valid PEMs
5	Expired certificates (fail-closed)
```
## Typical CI/CD Integration
```yaml
steps:
  - name: Verify trust store
    run: |
      python scripts/builder.py --env prod --bundle internal --verify-only
```

Use non-zero exit codes to gate pipelines when untrusted certificates are detected.