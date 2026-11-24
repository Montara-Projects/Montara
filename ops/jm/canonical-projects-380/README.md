# Issue #380 — Canonical slot on video-project save (JM prototype)

This is an **interim, fail-closed duplicate prevention** candidate for the LAB-JM Owner browser; it is NOT a complete #380 implementation and must not be promoted to MAIN/FER.

## Behavior

1. If the user is editing a previously opened project, preserve its actual `project_id` and verify it is still the Engine-selected project before draft. Refuse implicit title changes.
2. For a new tab/flow, compare a canonical normalized title (Unicode NFKC, trimmed whitespace, case insensitive) with Owner-scoped saved Video projects. If exactly one match, open it with the already-existing Owner-scoped Engine endpoint, then save the draft to the same project path. If none, create one new project. If multiple historical matches, **fail closed and ask the user to select the intended version** in Your Projects. No duplicate is hidden or deleted. Audio-only projects remain handled by #379.
3. Additional cameras and master audio pass to `register_selected_inputs` in the existing Engine draft, which invalidates affected stage artifacts according to Engine rules. All video outputs and prior JSON remain preserved until the Engine updates the selected project.

## Important limitations blocking acceptance

- This browser-only selection does NOT provide atomic server-side uniqueness for two tabs concurrently creating the same new name. It also does NOT provide a transactional optimistic project revision on every `wizard/draft` or other write. Treat it as an isolated partial pilot, not completion of the issue. Resolve with a server/Engine guarded create-or-open API and CAS/versioned updates before any MAIN promotion.
- Renaming and Duplicate As New need explicit controls and backend semantics. Legacy same-title projects require manual reconciliation, never destructive merge or silent display filtering.
- No deletion, media movement, R2 migration, public routing or changes to FER/MAIN.

## Deployment

The active JM JS is NOT equivalent to the repository JS. `active_web_montara.js` is a surgical merge into the exact pinned active `web/montara.js` SHA `0ea9c8794591564565a716bb99a9791624fabf47093f05751aab9e3d2662680a`, preserving other fixes. `build_jm_overlay.py` can stage an independent immutable root-owned copy and updates only digest pins. No unit is reloaded until Owner workers are idle and E2E accepted.
