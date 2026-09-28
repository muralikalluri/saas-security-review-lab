# dependency-scan

> Deliberately insecure for demonstration. Do not deploy. Run locally only.

Trivy against lockfiles/manifests only - see the top-level `scanners/README.md`
for the full writeup (scope, why lockfiles not `node_modules/`, why this
isn't gated in CI). Outputs: `../results/dependency-scan/*.json`.

```bash
trivy fs --scanners vuln --format json \
  --output ../results/dependency-scan/tenant-api.json \
  ../../targets/tenant-api/pom.xml

trivy fs --scanners vuln --format json \
  --output ../results/dependency-scan/tenant-api-fixed.json \
  ../../targets/tenant-api-fixed/pom.xml

trivy fs --scanners vuln --format json \
  --output ../results/dependency-scan/vibe-app.json \
  ../../targets/vibe-app/package-lock.json
```
