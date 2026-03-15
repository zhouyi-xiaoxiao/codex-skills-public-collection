name: teaching-hours-claim-skill
description: Reconstruct teaching, marking, support-session, meeting, training, and admin hours for higher-education hours claims from email evidence and contract messages. Use when Codex needs to recover work for a course or unit, identify the official unit name or code and department, determine the likely role family, estimate hours from script counts, sessions, meetings, or prep, or draft approval and claim emails.
---

# Teaching Hours Claim Skill

## Overview

Use email evidence to rebuild a teaching-hours narrative for a taught unit, calculate a defensible total, identify the likely role bucket, and draft the approval email or explanation the user needs.

## Workflow

### 1. Build the unit context

- Search the mail source for the course title, common shorthand, unit code, and course-lead surname.
- Prefer notifications from the virtual learning environment when possible; they often expose the exact unit title and code.
- Search allocation, contract, payroll, HR, and claim-system emails to map the unit to the correct department and role family.
- Do not assume all units in the same term share the same department or role family; check each unit separately.
- Distinguish the generic claim form from the underlying role. Institutions often use one catch-all hours form even when the contract itself uses a more specific role label.
- When the user has multiple contracts, do not assume the unit uses the same role as the last claim. Tie the unit to the contract family using department, unit code, and contract language.

### 2. Recover the work completed

- Search the mail source for work keywords around the unit: `formative`, `assessed`, `marking`, `course site`, `VLE`, `problem class`, `support session`, `rubric`, `temporary scores`, `scripts`, `copies`, `merge`, `final entry`.
- Also search for other common teaching-work patterns: `meeting`, `training`, `onboarding`, `floorwalking`, `lab`, `tutorial`, `seminar`, `workshop`, `session delivery`, `preparation`.
- Treat the user's own emails volunteering for or confirming a task as strong evidence that they took that work.
- Treat later emails saying marks were uploaded, merged, or completed as strong evidence that the work was finished.
- For marking, capture:
  - total submissions
  - which question(s) or script range the user handled
  - whether the user also did final entry, temporary scores, or course-site admin
- For teaching/support, capture:
  - session date
  - nominal session duration
  - prep hints such as worksheets, solutions, room changes, or helper instructions
- For meetings, training, or onboarding, capture:
  - date
  - stated duration or calendar duration
  - whether follow-up prep or materials review should be counted separately
- Summarize the evidence per activity with concrete dates before estimating hours.

### 3. Estimate hours

- Use course-owner estimates first when they exist.
- Fall back to generic formulas only when course-specific estimates are missing or clearly rough.
- Count each activity under the category that best matches the evidence: marking, taught session, support session, lab/tutorial, meeting, training/onboarding, or admin.
- Keep task-specific admin inside the relevant marking item when it is obviously part of that task.
- Add a separate miscellaneous admin line only for leftover coordination not already counted elsewhere.
- Show the arithmetic explicitly when the user wants to defend the number to a colleague or unit director.
- If several reasonable estimates exist, present:
  - the strict budget-style estimate
  - a conservative actual-time estimate
  - the recommended claim number

Read [references/calculation-rules.md](references/calculation-rules.md) when estimating hours.

### 4. Determine the claim bucket

- Match the unit to the department first.
- Then match the department to the relevant contract email.
- Prefer the contract or contract-confirmation email that explicitly names the role.
- Call out conflicting evidence instead of hiding it.
- If the answer is still uncertain, tell the user which role is most likely and why.

### 5. Draft the output

- For a unit director approval email:
  - include the official unit name and code
  - include the department if that helps distinguish roles
  - state the total hours clearly
  - give a short breakdown
  - ask for a brief confirmation reply for the hours-claim system
- For a colleague explanation:
  - explain the formula in plain English
  - show the exact arithmetic
  - separate assumptions from email-confirmed facts
- For an internal payroll or claim note:
  - keep it concise
  - keep role and unit identification unambiguous

Read [references/email-templates.md](references/email-templates.md) when drafting.

## Search patterns

- Search unit identifiers in parallel:
  - `<course title>`
  - `<course shorthand>`
  - `<unit code>`
  - `<course lead surname>`
- Search work evidence in parallel:
  - `formative`
  - `assessed`
  - `marking`
  - `course site`
  - `VLE`
  - `problem class`
  - `support session`
  - `meeting`
  - `training`
  - `onboarding`
  - `tutorial`
  - `workshop`
  - `lab`
  - `rubric`
  - `temporary scores`
- Search role evidence in parallel:
  - `hours claim`
  - `payroll`
  - `contract`
  - `claim`
  - `teaching assistant`
  - `demonstrator`
  - `hourly teacher`
  - `<department name>`

## Output habits

- Use absolute dates in the final explanation when the timeline could be confused.
- Tell the user which facts came directly from email evidence and which numbers are estimates.
- Search for the user's previous approval emails to similar course leads when matching tone or format would help.
- Do not overfit to one department's vocabulary; the same workflow should work across multiple teaching units and institutions.
- Prefer a defensible number over an aggressive number.
