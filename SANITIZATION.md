# Sanitization Log

This public repository was assembled from a separate set of working repositories and published with fresh history only.

## Source packages

- `gmail-gws-codex-kit`
- `bristol-claim-teaching-hours`
- `codex-secure-skills`
- `codex-portable-config`

## What was done

- original private repositories were not flipped to public as part of this release
- package contents were re-exported into a new public monorepo with fresh commits
- tracked host-specific env files were removed from the public collection
- usernames, personal home paths, tenant IDs, backup paths, and cluster aliases were replaced with placeholders
- institution-specific examples in the teaching-hours package were generalized into reusable teaching-claim wording
- example emails, subjects, and dates in browser automation docs were replaced with neutral placeholders

## What remains intentionally generic

- package names that describe the workflow
- example file paths such as `~/.config/...` when they are standard local-only locations
- skill structures, scripts, and references needed for the packages to remain usable

## Provenance note

The package names listed above are included here as provenance only. They are not public installation targets for this collection.
