# Teaching Hours Claim Skill

This package contains a reusable Codex skill for reconstructing teaching-hour claims from email evidence and drafting approval or explanation emails.

## What it covers

- taught-session and support-session time
- marking and partial marking allocations
- meetings, training, onboarding, and admin
- role-bucket inference from contracts and claim emails
- concise draft messages for approval or payroll notes

## Install

From the monorepo root:

```bash
mkdir -p "$HOME/.codex/skills"
cp -R packages/teaching-hours-claim-skill "$HOME/.codex/skills/teaching-hours-claim-skill"
```

## Package contents

- `SKILL.md`: the skill instructions
- `references/calculation-rules.md`: estimation rules and formulas
- `references/email-templates.md`: reusable approval and explanation templates
- `agents/openai.yaml`: metadata for agent integration

The examples in this package are intentionally generic and should be adapted to the local institution, claim system, and course vocabulary.
