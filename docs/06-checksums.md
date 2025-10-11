# Verifying Checksums

Each build output directory includes a file called `checksums.sha256`
containing SHA256 digests of every artifact produced by the build. Use these checks to confirm artifact integrity when copying or publishing bundles.

(Below examples assume the output dir is `build/prod/internal`)

## 🐧 Linux / macOS (bash)
```bash
cd build/prod/internal
sha256sum -c checksums.sha256
```
### Output
```
ca-trust.pem: OK
ca-trust.jks: OK
ca-trust.p7b: OK
```

## 🪟 PowerShell (Windows)
```powershell
cd build\prod\internal
Get-FileHash * -Algorithm SHA256 |
    ForEach-Object { "{0}  {1}" -f $_.Hash.ToLower(), $_.Path.Split('\')[-1] } |
    Out-File -Encoding ascii checksums.verify
# Compare manually:
Compare-Object (Get-Content .\checksums.sha256) (Get-Content .\checksums.verify)
```

## 🐍 Python
```python
import hashlib, pathlib
for f in pathlib.Path("build/prod/internal").glob("*"):
    if f.is_file():
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        print(f"{h}  {f.name}")
```

## 🔐 OpenSSL (alternative single file)
```bash
openssl dgst -sha256 build/prod/internal/ca-trust.pem
```

