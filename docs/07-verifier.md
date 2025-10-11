# Certificate Verification

`verify_certs.py` validates any PEM bundle for expiration, health, and policy compliance.

---

## 🧪 Usage

```bash
python scripts/verify_certs.py --file build/prod/internal/ca-trust.pem
```

#### Options
```Flag	Description
--file	PEM bundle path
--warn-days <N>	Warn if cert expires within N days (default 30)
--fail-on-expired	Exit non-zero if expired certs found
```