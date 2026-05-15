---
description: Run TestStat-CLI against Excel test specification files and return JSON summary output for agent-readable analysis
argument-hint: <xlsx-file-or-directory-or-list-yaml>
---

# TestStat-CLI JSON Summary

Use `tstat` to aggregate Excel test specification results for the requested target.

## Required command pattern

Always include the `--json` option so the output is machine-readable:

```bash
tstat --json <xlsx-file-or-directory>
```

For a project list file, use:

```bash
tstat --json --list <project-list.yaml>
```

If a custom config file is needed, use:

```bash
tstat --json --config <config.json> <xlsx-file-or-directory>
```

## Agent instructions

1. Resolve the user's target path relative to the current workspace.
2. Prefer `tstat --json ...` for all executions from this command.
3. Parse the JSON output before summarizing results.
4. Report the key counts: total cases, available cases, completed, executed, completion rate, execution rate, warnings, and per-file breakdown when present.
5. If `tstat` exits with an error, read stderr/stdout and explain the missing path, config issue, or unsupported file condition.

Do not run plain table output from this command.
