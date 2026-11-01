# ADR 0004: Accounts and identity

**Status:** Accepted as a deviation from the Blueprint (1 Nov 2026)

## Context
The Blueprint plans managed identity with SSO (Phase 2). The prototype needed accounts earlier to
store each user's decision journal.

## Decision
Own accounts in the API for now: email and password, Argon2id hashes, opaque session tokens
stored only as SHA-256 hashes in an httpOnly SameSite=Lax cookie, rate-limited sign-in, an
origin check against cross-site writes, secure cookies required in production.

## Consequences
No SSO, MFA, password reset or email verification yet. Before public launch, move to a managed
identity provider (SSO, MFA, organisation accounts for institutions) and migrate users; the
session check in `app/core/auth.py` is the single place that changes.
