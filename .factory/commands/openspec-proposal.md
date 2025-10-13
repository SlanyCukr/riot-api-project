---
description: Scaffold a new OpenSpec change and validate strictly
argument-hint: <change-id>
---

# OpenSpec: Proposal

Create a new OpenSpec change proposal with ID: `$ARGUMENTS`

## Guardrails
- Favor straightforward, minimal implementations first and add complexity only when it is requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `openspec/AGENTS.md` (located inside the `openspec/` directory—run `ls openspec` or `openspec update` if you don't see it) if you need additional OpenSpec conventions or clarifications.
- Identify any vague or ambiguous details and ask the necessary follow-up questions before editing files.

## Proposal Creation Steps

1. **Review current state**: Check `openspec/project.md`, run `openspec list` and `openspec list --specs`, and inspect related code or docs (e.g., via grep/ls) to ground the proposal in current behaviour; note any gaps that require clarification.

2. **Scaffold structure**: Choose a unique verb-led `change-id` and scaffold `proposal.md`, `tasks.md`, and `design.md` (when needed) under `openspec/changes/$ARGUMENTS/`.

3. **Map capabilities**: Map the change into concrete capabilities or requirements, breaking multi-scope efforts into distinct spec deltas with clear relationships and sequencing.

4. **Document architecture**: Capture architectural reasoning in `design.md` when the solution spans multiple systems, introduces new patterns, or demands trade-off discussion before committing to specs.

5. **Draft spec deltas**: Create spec deltas in `openspec/changes/$ARGUMENTS/specs/<capability>/spec.md` (one folder per capability) using `## ADDED|MODIFIED|REMOVED Requirements` with at least one `#### Scenario:` per requirement and cross-reference related capabilities when relevant.

6. **Draft tasks**: Create `tasks.md` as an ordered list of small, verifiable work items that deliver user-visible progress, include validation (tests, tooling), and highlight dependencies or parallelizable work.

7. **Validate**: Run `openspec validate $ARGUMENTS --strict` and resolve every issue before sharing the proposal.

## Reference
- Use `openspec show <id> --json --deltas-only` or `openspec show <spec> --type spec` to inspect details when validation fails.
- Search existing requirements with `grep -r "Requirement:|Scenario:" openspec/specs` before writing new ones.
- Explore the codebase thoroughly so proposals align with current implementation realities.
