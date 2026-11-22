# JM #380 — Atomic project identity and native writer gates

Date: 2026-11-22. **DRAFT stacked on PR #385; NOT activated in JM, FER or MAIN.**

## Existing issue

The PR #385 browser title lookup is not atomic: two tabs can both see no project and start two native project folders under the same name. A project is a persistent editable identity, not a filename or browser-created slot. Old duplicate titles may contain different edits and cannot be merged or deleted automatically.

## Implemented server-side foundation

- New module: urano/owner_project_slot_registry.py.
- Private Owner SQLite, BEGIN IMMEDIATE transactions, immutable UUID and unique constraint on normalized (owner, kind, title). Unicode NFKC, casefold and whitespace title normalization; audio and video titles independent.
- Atomic create reservation: concurrent same-name creation fails with conflict. A reserved slot is not considered a fully opened project.
- Explicit rename with expected_revision CAS; rejects title conflicts and stale tabs. Stable ID and native reference retained. Only updates the canonical catalog until native rename integration is done.
- Explicit duplicate_as_new creates a NEW reserved UUID, never an alias to source native files. A privileged copier must create/verify a distinct native folder before activating the copy.
- Internal bind_native_verified refuses arbitrary re-binding or sharing one native reference across slots. The calling privileged service MUST independently verify Owner's native project; no browser flag can be trusted.
- Revisioned snapshot SHA256 receipts and persistent reload/reopen of metadata. No original media modified.
- Native writer guard uses private 0700 lock directory and 0600 file with O_NOFOLLOW, cross-process flock spanning revision validation, trusted atomic/fsynced native writer and metadata CAS; stale writer does NOT run. Callbacks come from the trusted server, never the client.

## Tests performed

22 new tests PASS locally on macOS (real SQLite): 8 simultaneous new creates, two simultaneous snapshot saves, two whole-write races, Owner separation, audio/video same name, Unicode collision, rename/duplicate revisions, stale writer blocked, restart persistence, private lock validation, unchanged original media. Five previous ProjectCatalog tests PASS and existing PR #385 Node selection tests PASS.

Attempt to repeat on Linux VM was interrupted by SSH disconnect before test files could be transferred. No Linux validation is claimed.

## Remaining release gates

- [ ] Wire native Engine create, /wizard/draft, Save/Update/Add/Remove Input and Stage edits to the new registry AND the full native writer lock. Require a per-project expected_revision from each enabled UI operation; reject legacy bypasses. Metadata CAS alone does not stop overwriting a native file.
- [ ] Implement native rename (update project.json) and independent non-destructive duplication (copy edits/media references safely and verify another native folder). Expose explicit Rename and Duplicate As New UI buttons, not implicit rename-by-typing.
- [ ] Reconcile historical same-title projects after Owner inventory and user review; never auto-merge/hide/delete.
- [ ] Integrate PR #384 audio project persistence without mixing multi-song session identity.
- [ ] Authenticated JM E2E: create video+audio, save, refresh, reopen, revise, add source, save, reopen; two-tab name and revision races; explicit rename/copy/reopen; Companion/export integrity, permissions and rollback. FER review, Windows QA and isolated Linux test required.
- [ ] No public MAIN promotion until these gates pass; GitHub Actions #372 remains blocked separately.

## Accurate status

**Server-side Owner metadata uniqueness, CAS revisions, safe native writer-lock API and reserved rename/duplicate semantics completed in code with local tests.** No live Stage path currently invokes this API. The native filesystem writer, UI actions and authentic saved-video E2E are still pending. Keep issue #380 In Progress. Original JM/FER/MAIN services and project data untouched.
