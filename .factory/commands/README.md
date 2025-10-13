# Custom Factory.ai Droid Commands

This directory contains custom slash commands for the Factory.ai droid CLI. These commands are project-specific and shared with all team members.

## Available Commands

### OpenSpec Commands

These commands help manage OpenSpec change proposals and implementation:

#### `/openspec-proposal <change-id>`
**Description:** Scaffold a new OpenSpec change and validate strictly

Creates a new OpenSpec change proposal with the specified change ID. This command guides you through:
- Reviewing current state and specs
- Scaffolding the proposal structure
- Mapping capabilities and requirements
- Documenting architecture decisions
- Drafting spec deltas and tasks
- Validating the proposal

**Usage:**
```
/openspec-proposal add-player-stats-api
```

#### `/openspec-apply <change-id>`
**Description:** Implement an approved OpenSpec change and keep tasks in sync

Implements an approved OpenSpec change by following the proposal's tasks and design. This command:
- Reads the proposal, design, and tasks
- Works through tasks sequentially
- Keeps edits minimal and focused
- Updates task statuses upon completion

**Usage:**
```
/openspec-apply add-player-stats-api
```

#### `/openspec-archive <change-id>`
**Description:** Archive a deployed OpenSpec change and update specs

Archives a completed and deployed OpenSpec change. This command:
- Moves the change to the archive
- Updates canonical specs
- Validates the result
- Preserves change history

**Usage:**
```
/openspec-archive add-player-stats-api
```

## How Commands Work

- Commands are Markdown files with optional YAML frontmatter
- The `$ARGUMENTS` variable expands to everything typed after the command name
- Commands are automatically discovered on CLI launch
- Press `R` in the `/commands` UI to reload without restarting

## Adding New Commands

1. Create a new `.md` file in this directory
2. Add optional YAML frontmatter with `description` and `argument-hint`
3. Write your command template using `$ARGUMENTS` for parameter substitution
4. The filename becomes the command slug (e.g., `my-command.md` → `/my-command`)

## Reference

For more information on custom commands, see:
- [Factory.ai Custom Commands Documentation](https://docs.factory.ai/cli/configuration/custom-commands)
- Project OpenSpec documentation in `openspec/AGENTS.md`
