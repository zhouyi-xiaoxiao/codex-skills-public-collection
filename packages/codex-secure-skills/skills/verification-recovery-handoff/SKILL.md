---
name: verification-recovery-handoff
description: "Handle legitimate signup and login verification through email links, session reuse, and first-party OAuth callbacks. Use when onboarding is blocked by split-domain auth, delayed verification mail, or anti-abuse gates that require a safe human handoff instead of CAPTCHA bypass."
---

# Verification Recovery Handoff

## Overview

Use this skill when an onboarding flow stalls on verification rather than on the core product itself. The goal is to recover progress through legitimate first-party mechanisms and to pause cleanly whenever the remaining step truly requires the user.

## Workflow

### 1. Start with the normal path

- Try the ordinary signup or login flow first.
- Confirm which requirement the user actually needs to satisfy: account creation, verified email, dashboard access, billing setup, or API key creation.
- Avoid jumping into frontend inspection until the standard path clearly fails or loops.

### 2. Recover through email before escalating

- Search the inbox for verification emails, magic links, passwordless login links, or approval prompts.
- Prefer first-party verification links over manual OTP entry when both are available.
- If several messages exist, use the newest unexpired link and confirm the target host is first-party.

### 3. Reuse legitimate authenticated state

- Check whether the user is already signed in on a related first-party domain.
- Inspect cookies, local storage, and current browser state only for the target service's own domains.
- When split-domain auth is involved, look for first-party authorize and callback URLs that bridge the authenticated host to the product console.

### 4. Inspect first-party auth flows carefully

- If the browser UI is stuck, inspect the target site's own network requests or frontend bundle for:
  - verification endpoints
  - authorize endpoints
  - callback routes
  - state and redirect parameters
- Use only legitimate first-party flows that the site already exposes.
- Do not fabricate tokens, replay someone else's session, or tamper with anti-abuse challenges.

### 5. Hand off when the user must act

Stop and hand control back for:

- hard CAPTCHA or other human-verification puzzles
- SMS, passkey, biometric, hardware-key, or app-based 2FA challenges
- payment confirmation or `3DS`
- legal, financial, or identity approvals that the user must accept personally

When you hand off:

- leave the browser on the exact page or modal that needs action
- tell the user exactly what remains
- resume immediately after the user confirms completion

## Safety Boundary

- Never use CAPTCHA-solving services, SMS rental, proxy farms, or browser fingerprint spoofing.
- Never claim to have completed a human-verification step that was actually bypassed or skipped.
- Never publish notes that contain private emails, tokens, callback URLs with live secrets, or account-specific recovery links.

## Completion Checklist

- the account exists
- the verified state is confirmed
- dashboard or console access is restored
- the next blocker, if any, is clearly isolated for the user
