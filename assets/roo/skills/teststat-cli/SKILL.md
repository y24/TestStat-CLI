---
name: teststat-cli
description: Use TestStat-CLI to aggregate Excel test specification results from xlsx files, folders, or YAML project lists with JSON output for agent-readable summaries.
---

# TestStat-CLI Skill

Use this skill when the user asks to inspect, summarize, aggregate, or report test execution status from Excel test specification files using TestStat-CLI.

## Core rule

Always run TestStat-CLI with the `--json` option when acting as an AI agent:

```bash
tstat --json <xlsx-file-or-directory>
```

For a YAML project list:

```bash
tstat --json --list <project-list.yaml>
```

For a custom configuration:

```bash
tstat --json --config <config.json> <xlsx-file-or-directory>
```

## Workflow

1. Identify whether the user provided an `.xlsx` file, a directory, or a YAML project list.
2. Confirm the path exists before running `tstat` when the shell environment allows it.
3. Run `tstat` with `--json` and the relevant path or `--list` option.
4. Parse the JSON result.
5. Summarize the results in user-facing language.

## JSON fields to inspect

- `summary_results`: processed files, case counts, status dates, and overall execution metadata.
- `total_results`: status counts, incomplete count, completed count, executed count, completion rate, and execution rate.
- `file_breakdown`: per-file results when multiple files are processed.
- `warnings`: skipped files, missing paths, or other non-fatal issues.
- `error`: fatal errors that prevented processing.

## Reporting guidance

When results are available, report:

- total cases and available cases
- completed and executed counts
- completion rate and execution rate
- major failing or blocked result counts when present
- warnings or errors
- per-file outliers when `file_breakdown` exists

Avoid relying on table-formatted output because it is harder for agents to parse reliably.
