# gitleaks — targets/vibe-app-fixed current tree

> Deliberately insecure for demonstration. Do not deploy. Run locally only.

`gitleaks dir` (working-tree scan, not `git` history mode - see
`scanners/README.md` for why `git` mode is a separate, intentionally
different check) against `targets/vibe-app-fixed`, after removing local
build artifacts (`.next/`, `*.tsbuildinfo`). Raw output: `vibe-app-fixed-tree.json`.

Cross-referenced against `git ls-files targets/vibe-app-fixed`:

| | Count |
|---|---|
| Hits in git-tracked files | **0** |
| Hits in untracked files (the local, gitignored `.env`) | 3 |

The 3 untracked hits are the local `.env` a developer creates from
`.env.example` to run the app - expected to contain real-shaped local
Supabase demo credentials, never committed (confirmed by
`targets/vibe-app-fixed/exploits/B-02-secrets-committed.sh`). Zero hits in
anything git actually tracks.
