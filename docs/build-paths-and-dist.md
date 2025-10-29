# Build Paths and Reserved Directories

This guide explains how BundleCraft determines build output locations, how to customize paths safely, and which directories/files are reserved or managed by the build system.

## Output Root: dist/

All build outputs are rooted under the repository’s `dist/` directory. This directory is automatically managed by BundleCraft and should not contain user-created files.

Typical structure (default paths):

```plaintext
dist/
  <environment>/
    <bundle>/
      bundlecraft-ca-trust.pem
      bundlecraft-ca-trust.p7b
      bundlecraft-ca-trust.jks
      bundlecraft-ca-trust.p12
      manifest.json
      checksums.sha256
      sbom.json
      package.tar.gz
      *.asc  # Optional signatures if signing enabled
```

## Customizing Build Paths (env.build_path)

You can customize where bundles are written within `dist/` using the `build_path` key in your environment config (e.g., `config/envs/dev.yaml`).

Example:

```yaml
# config/envs/dev.yaml
build_path: dev/custom/
```

Resulting layout (for bundle `internal`):

```plaintext
dist/
  dev/custom/
    internal/
      ...
```

### Safety and normalization

- The path is always rooted under `dist/`, even if `build_path` is set.
- Leading slashes and `..` segments are stripped.
- If you include a `dist/` prefix, it is removed. For example, `dist/dev/custom/` is treated as `dev/custom/`.
- If, after normalization, the path attempts to escape `dist/`, the build will fail with a clear error.

### Manifest field: build_path

Each built bundle includes a `manifest.json` file. The manifest now records the effective environment build base under `dist/` using a `build_path` field.

Example `manifest.json` excerpt:

```json
{
  "env": "TestEnv",
  "bundle": "internal",
  "build_path": "dist/TestEnv",
  "certificate_count": 42,
  "output_formats": ["pem", "p7b"]
}
```

- When `env.build_path` is omitted, `build_path` defaults to `dist/<env-name>`.
- When `env.build_path` is set (e.g., `team/dev/custom/`), `build_path` becomes `dist/team/dev/custom`.
- This is the base directory under which per-bundle folders are created (e.g., `dist/TestEnv/<bundle>/...`).

## Reserved and managed files

BundleCraft generates and manages several files inside each bundle directory. Some files are excluded from packaging to ensure deterministic and minimal artifacts:

- Excluded from `package.tar.gz`:
  - `manifest.json`
  - `checksums.sha256`
  - `metadata.yaml`
  - `sbom.json`
  - `README.md`
  - Signature sidecars: `*.asc`, `*.sig`

These exclusions keep the tarball stable and focused on the bundle artifacts.

## Guidelines for dist/

- Don’t place user files under `dist/`; it is managed by BundleCraft.
- In version control, prefer excluding `dist/` (via `.gitignore`) and publishing artifacts through CI/CD instead of committing them.

## CI/CD notes

- Artifacts from `dist/` can be published by your pipeline (e.g., GitHub Releases, OCI registries, artifact stores).
- The `manifest.json` includes checksums for traceability; `checksums.sha256` provides a flat list for quick verification.
