# Codex Skills Public Collection

A skill is a small package a coding agent loads when a task calls for it: a `SKILL.md` that says when and how to act, plus the scripts and reference notes it needs. This repository holds four packages for OpenAI's Codex CLI (a coding agent that runs in the terminal), published for anyone to reuse; two of them assume macOS.

They come from a larger private set. What is here was re-exported with fresh history, and usernames, home paths, hosts and institution-specific details were replaced with placeholders ([SANITIZATION.md](SANITIZATION.md) lists what was done). Published 15 March 2026; MIT licence since October 2026. Provided as is.

## Packages

- **[gmail-gws-codex-kit](packages/gmail-gws-codex-kit/)**: Gmail for Codex through a Google Workspace CLI (`gws`) wrapper that refreshes its own OAuth token, plus a `gmail-gws` skill. Needs `bash`, `python3` and your own Google OAuth desktop client; `npm` optional.
- **[teaching-hours-claim-skill](packages/teaching-hours-claim-skill/)**: rebuilds a teaching-hours claim (sessions, marking, meetings, training) from the evidence in your email and drafts the approval or explanation message. For tutors, markers and other hourly-paid teaching staff.
- **[codex-secure-skills](packages/codex-secure-skills/)**: two skills that keep a person in control of their own accounts. One backs up and updates saved logins in Chromium-style password stores without ever writing plaintext; the other gets a stalled sign-up or login moving again through the service's own verification emails and sign-in links, and hands back to the user at CAPTCHA, two-factor and payment steps. Needs `python3`.
- **[codex-portable-config](packages/codex-portable-config/)**: a template for keeping one Codex and MCP configuration across several Macs (per-host settings, profiles, sync and health checks), with two example skills, one for replying to Outlook mail and one for running jobs on a SLURM cluster. Needs `bash`, `python3` and Codex.

## Using a package

```bash
git clone https://github.com/zhouyi-xiaoxiao/codex-skills-public-collection.git
cd codex-skills-public-collection
```

Read the package's own `README.md`, then copy the skill folder you want into `~/.codex/skills/`. Keep OAuth files, tokens, cookies, local databases and host env files on your own machine; none of them belong in a copy of this repository. [SECURITY.md](SECURITY.md) has the rest.

---

Xiaoxiao Zhouyi · [zhouyixiaoxiao.com](https://zhouyixiaoxiao.com/)
