# Projects v2 — persistent handoff and coordination contract (PROPOSED)

**Status:** proposed by FER for JM review (19 Nov 2026). This document adds an entrypoint; it does **not** supersede `docs/COLLABORATION.md`, `AGENTS.md`, `CLAUDE.md`, either lab STATUS or decisions in issue #216.

## Canonical index and meaning

- **Project:** https://github.com/orgs/Montara-Projects/projects/1 (**private**). Project cards are an index of existing issues/PR and private draft ideas, **not** the technical source of truth.
- **Code/evidence/acceptance:** commits, PR, CI logs, tests, deployed versions, human E2E and their linked issues.
- **Shared coordination:** issue #216 and collaboration protocol. Keep each lab's STATUS and history under its own owner.
- **Never put credentials, internal routing details, private Google identities, private files or security-sensitive information into the PUBLIC repository/issue/PR.** The Project is private but its linked repo issues/PR are public.

## Current Project schema (verify live, do not assume future schema)

- `Status`: Todo / In Progress / Done, currently default.
- `Priority`: P0 - Critical / P1 - High / P2 - Normal / P3 - Later.
- `Area`: Coordination / Stage / Companion / Engine / Music / Cloudflare / Infrastructure / Security / QA.
- `Owner`: FER / JM / Joint / Unassigned (human accountable side, **not** the AI identity).
- `Validation`: Not started / Needs evidence / Human E2E / Verified / Blocked.
- Views: `00 · Todas las tareas`, `01 · Kanban`, `02 · Responsables`, `03 · Prioridades`, `04 · Ideas y futuro`. The last view uses `is:draft` so it contains only **draft issues and draft PRs**, including private project draft ideas. Filters/grouping of the other views may need final UI configuration.
- Pilot began with 12 linked tasks; `Area` and `Owner` classified as reference. **Do not assume all `Todo` statuses reflect progress, or that null priorities mean P3.**

## Start of each agent/chat

1. Read `AGENTS.md`, `CLAUDE.md`, `docs/COLLABORATION.md`, the relevant STATUS and other lab's STATUS, plus this document.
2. Fetch the live Project, focusing on the relevant `Owner`, status, blockers and validation. If project access fails, say so explicitly and use relevant issues/PR as fallback. Do **not** invent a current snapshot.
3. Before choosing work, inspect issue #216, linked discussion/reviews, current `origin/main`, branches, CI, submodule pins and the **actually deployed** version where relevant. Check the other lab's work to prevent duplication.
4. Choose one scoped task; agree cross-team/architecture/deployment decisions with both human owners according to collaboration rules. Board placement never constitutes deployment authorization.

## During and after a task

- Keep scope, technical proof, tested environment/versions, blockers and next owner in its **linked issue/PR**. Update `Status`, `Priority`, `Validation` only when grounded; avoid assignments or priority changes to the other human's work without agreement.
- `Verified` should name **what** was verified, by whom and where. A green unit test or merged PR is not human E2E; a successful lab E2E is not automatic MAIN deployment.
- A blocked card needs the cause, responsible party and precise next action, recorded in the linked issue/PR. Do not create duplicate issues for PR and underlying deliverable unless scope genuinely differs.
- Handoff in 5–10 lines: purpose; issue/PR and commit(s); what changed; exact PASS and environment; what is NOT verified; blocker/approval; next action and owner; links to evidence. Keep STATUS-JM and STATUS-FER separately maintained by their own teams.
- Private future ideas: use **Project draft issues** to avoid publishing sensitive product hypotheses in public repo issues. Draft *pull requests* can also match `is:draft`; the ideas view is not a formal Horizon roadmap.

## UI finishing steps (not automated via existing GraphQL configuration)

- `01 · Kanban`: verify grouping by `Status`.
- `02 · Responsables`: group by `Owner`.
- `03 · Prioridades`: sort/group by `Priority` **only after priorities are agreed**.
- Keep `04 · Ideas y futuro` filtered `is:draft`.
- Review item states with both humans before declaring anything in progress, blocked or done.

## Minimal success criterion

A new authorized AI can find the same board, trace an item to its technical evidence and leave a precise handoff; both humans retain decision-making, no unapproved infrastructure changes occur, and changing the chat does not silently change the source of truth.
