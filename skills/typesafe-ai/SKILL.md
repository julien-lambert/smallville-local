---
name: typesafe-ai
license: MIT
description: Project-local TypeSafe/Jev integration guidance and pointers to official skill.
---
# TypeSafe / Jev — guidance for Smallville Local

This is a concise **project-specific adaptation** of TypeSafe AI's public skill guidance, not a substitute for the full official skill. The canonical skill is at https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md (MIT); on a connected developer machine, install its current version with `npx skills add typesafe-ai/skills --skill typesafe-ai`.

## Principles

- Use Jev for typed *judgments* about the state supplied by the client, then choose the action in inspectable Python code, not in opaque language-model output.
- State must be small, structurally named, relevant, and reflect what the agent actually knows. Never send another agent's private memories.
- One independent judgment per question. Combine Choice, Noul and Score questions sharing the same state into one call.
- Do not confuse `confidence` with correctness. Interpret Noul as a model probability and leave ambiguous probability ranges for code to handle.
- Keep criteria, thresholds, and rules versioned in a single module (`smallville/jev.py`). Ensure every judgment combination maps to an action.
- Use clear options (`kind`, `hurtful`) rather than positional labels. Design Score levels as complete scenarios.
- If using `Box`, pair it with a Noul presence check. Images and Box need `TypeSafe-Danger-Zone-Images: true`; unnecessary for this simulator because visual world state is already structured.
- When testing the live API, obtain user permission, a budget, and disclose data sent. Never test using a user's personal API key without explicit consent.
- Jev calls must use `POST https://api.typesafe.ai/v1/systemone` only, no redirects, no automatic retries and a bounded payload. Keep the API key server-side and do not expose it in JavaScript, logs, exports, or errors.
- Fail closed on uncertain billing. Preserve the budget ledger across world resets. No fallback cloud provider.

Official references: https://docs.typesafe.ai/api/system-one · https://docs.typesafe.ai/primitives/choice · https://docs.typesafe.ai/primitives/noul · https://docs.typesafe.ai/primitives/score · https://docs.typesafe.ai/models
