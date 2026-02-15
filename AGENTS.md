# AGENTS.md

Guidance for AI coding assistants working in this repository.

When answering questions, respond with high-confidence answers only: verify in code; do not guess.

## Workflow

Use GitHub Issue stage labels as the source of truth for queue state:
- `stage:backlog`
- `stage:queued`
- `stage:needs-clarification`
- `stage:ready-to-implement`
- `stage:in-progress`
- `stage:in-review`
- `stage:blocked`

## Security

Never commit or publish real phone numbers, videos, or live configuration values. Use obviously fake placeholders in docs, tests, and examples.

## Commit Guidelines

1. Every completed code/doc change must be committed in an atomic commit before moving to the next task.
2. Always commit your own changes immediately after tests/checks pass for that change.
3. Never batch unrelated changes into one commit; keep scope tightly focused.
4. Use concise, action-oriented conventional commit messages.
5. Link each commit to its issue by including `#<issue_number>` in the commit subject or body.
6. Prefer closing keywords (`Closes #<issue_number>`, `Fixes #<issue_number>`) on the final commit that fully resolves the issue.
7. Stage only the files that belong to your change.

## Testing Guidelines

### TDD (strict)
1. **RED**: write a failing test first.
2. **GREEN**: implement minimal code to pass tests.
3. **REFACTOR**: improve quality while keeping tests green.
4. **COMMIT**: only commit when tests pass.

## Multi-agent safety

do not create/apply/drop git stash entries unless explicitly requested.
do not switch branches unless explicitly requested.
when the user says "commit", scope to your changes only.
when unrelated changes exist, keep going and commit only your own files.
