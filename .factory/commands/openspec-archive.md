---
description: Archive a deployed OpenSpec change and update specs
argument-hint: <change-id>
---

# OpenSpec: Archive

Archive the deployed OpenSpec change with ID: `$ARGUMENTS`

## Guardrails
- Favor straightforward, minimal implementations first and add complexity only when it is requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `openspec/AGENTS.md` (located inside the `openspec/` directory—run `ls openspec` or `openspec update` if you don't see it) if you need additional OpenSpec conventions or clarifications.

## Archive Steps

1. **Identify change**: Confirm the change ID `$ARGUMENTS` (via the prompt or `openspec list`).

2. **Run archive command**: Execute `openspec archive $ARGUMENTS --yes` to let the CLI move the change and apply spec updates without prompts (use `--skip-specs` only for tooling-only work).

3. **Review output**: Review the command output to confirm the target specs were updated and the change landed in `openspec/changes/archive/`.

4. **Validate**: Run `openspec validate --strict` and inspect with `openspec show $ARGUMENTS` if anything looks off.

## Reference
- Inspect refreshed specs with `openspec list --specs` and address any validation issues before handing off.
- The archive process should preserve the change history while updating the canonical specs.
