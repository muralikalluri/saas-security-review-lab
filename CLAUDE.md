# Project: saas-security-review-lab
Read SPEC.md first. Implement only the requested milestone.

## Rules
- Baseline targets are INTENTIONALLY vulnerable. Keep every seeded flaw listed in SPEC §2 and §4 unless the milestone is a "fixed" milestone.
- Fixed versions must close every finding; the isolation tester must be fully green.
- Never use real secrets. Seeded "leaked" secrets must be obviously fake and must NOT match real key formats (e.g. FAKE_STRIPE_SECRET_DO_NOT_USE), otherwise GitHub push protection blocks the push. For Supabase use only the local CLI demo keys.
- Nothing listens on 0.0.0.0 outside docker's internal network except the demo ports; README warns against deployment.
- Each finding ID (A-xx, B-xx) appears in code comments at the flaw location and in the fix commit message.
- All companies, users and data are fictional.

## MVP scope
Milestones M0-M7 in SPEC.md §7 are the MVP. Skip M8.
Do not implement anything marked "Later" in SPEC.md unless explicitly asked.

## Delegation
- Before building correctness-critical logic, consult the design-critic subagent.
- After finishing a milestone, run the milestone-reviewer subagent and fix every FAIL before summarising.

## Working style
- Implement ONLY the milestone named in the prompt. Stop when its acceptance criteria pass.
- Never weaken, skip or delete tests to make them pass. If a criterion seems wrong, stop and say so.
- End each milestone with: files changed, how to run/verify, anything left open.

## Ports and isolation
- All host ports for this repo use the 81xx range (define them in .env.example, never hardcode).
- docker-compose.yml sets `name: saas-security-review-lab` so container, volume and network names never clash with my other repos.
- Container-internal ports can stay standard (5432, 8080); only host-side mappings use 81xx.
