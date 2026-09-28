#!/usr/bin/env bash
# Deliberately insecure for demonstration. Do not deploy.
# The other half of B-02: gitleaks finds SECRETS inside a committed file,
# but ".env is tracked by git at all" is a separate, structural fact about
# .gitignore, not a string pattern - a real secret scanner (or gitleaks
# itself) can't see it. `git ls-files` is the ground truth for "will this
# be pushed", so we check it directly instead of guessing from .gitignore
# contents.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "Tracked .env files (expected: exactly targets/vibe-app/.env, per B-02 - deliberately committed):"
git ls-files | grep -E '(^|/)\.env$' || echo "(none found)"
