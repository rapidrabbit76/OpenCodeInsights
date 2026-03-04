---
description: Generate an OpenCode Insights report — analyzes your session history and produces an interactive HTML report with usage patterns, wins, friction points, and recommendations.
---

# OpenCode Insights Report Generator

You are generating a comprehensive insights report about the user's OpenCode usage patterns.
This report mirrors Claude Code's `/insights` output — a rich HTML report with charts, narratives, and actionable recommendations.

## Step 1: Collect Raw Metrics

Run the data collector to extract quantitative metrics from the OpenCode database.

The user may optionally specify:
- `--days N` to limit to last N days (default: last 14 days)
- `--project PROJECT_ID` to filter by project

```bash
python3 {{INSIGHTS_HOME}}/src/collector.py --days 14 -o {{INSIGHTS_HOME}}/output/raw_metrics.json
```

Read the output file to understand the raw data:
```bash
cat {{INSIGHTS_HOME}}/output/raw_metrics.json
```

## Step 2: Analyze and Generate Narratives

Read the raw metrics JSON carefully. You must generate AI narrative content by analyzing:
- Session summaries (titles, user messages, tools used, errors)
- Tool usage patterns
- Agent distribution
- Time patterns
- Error patterns

### Write the narratives JSON file

Create `{{INSIGHTS_HOME}}/output/narratives.json` with this EXACT structure:

```json
{
  "subtitle": "<user_messages> messages across <total_sessions> sessions | <date_start> to <date_end>",
  "at_a_glance": {
    "whats_working": "One paragraph analyzing what's going well based on session data — what the user excels at, which workflows are most successful.",
    "whats_hindering": "One paragraph analyzing friction points — what's causing errors, misunderstandings, or wasted time.",
    "quick_wins": "One paragraph with 2-3 immediately actionable suggestions based on the data.",
    "ambitious_workflows": "One paragraph describing advanced workflows the user could adopt as AI models improve."
  },
  "project_areas": [
    {
      "name": "Area Name",
      "session_count": 5,
      "description": "Description of what the user worked on in this area, synthesized from session titles and first messages."
    }
  ],
  "usage_narrative": {
    "paragraphs": [
      "First paragraph: Describe the user's overall working style — how they interact with AI, what patterns emerge from the data (e.g., long autonomous sessions, quick Q&A, team orchestration).",
      "Second paragraph: Describe specific habits — response times, tool preferences, multi-clauding patterns, session types."
    ],
    "key_pattern": "One sentence summarizing the user's key usage pattern."
  },
  "wins_intro": "One sentence introducing what went well, referencing specific metrics.",
  "wins": [
    {
      "title": "Win Title",
      "description": "Detailed description of an impressive thing the user accomplished, backed by data from the sessions."
    }
  ],
  "friction_intro": "One sentence introducing friction points, referencing specific metrics.",
  "friction_categories": [
    {
      "title": "Friction Category Name",
      "description": "Description of this type of friction and how to mitigate it.",
      "examples": [
        "Specific example from a session where this friction occurred."
      ]
    }
  ],
  "what_you_wanted": [
    {"name": "Task Type", "count": 5}
  ],
  "what_helped_most": [
    {"name": "Capability", "count": 3}
  ],
  "outcomes": [
    {"name": "Fully Achieved", "count": 8},
    {"name": "Mostly Achieved", "count": 4},
    {"name": "Partially Achieved", "count": 2}
  ],
  "friction_types": [
    {"name": "Type Name", "count": 3}
  ],
  "satisfaction": [
    {"name": "Likely Satisfied", "count": 15},
    {"name": "Dissatisfied", "count": 3}
  ],
  "claude_md_suggestions": [
    {
      "instruction": "Add under a ## Section Name section in CLAUDE.md or AGENTS.md",
      "text": "The actual directive text to add.",
      "why": "Why this suggestion would help, based on observed friction."
    }
  ],
  "features_to_try": [
    {
      "title": "Feature Name",
      "oneliner": "One line description of the feature.",
      "why_for_you": "Why this feature would specifically help THIS user, based on their data.",
      "examples": [
        {"code": "Code example or configuration snippet"}
      ]
    }
  ],
  "new_patterns": [
    {
      "title": "Pattern Name",
      "summary": "One sentence summary.",
      "detail": "Detailed explanation of the pattern and why it would help.",
      "prompt": "A copyable prompt the user can paste to try this pattern."
    }
  ],
  "horizon_intro": "One sentence about what's possible as AI models improve.",
  "horizon": [
    {
      "title": "Future Workflow Title",
      "possible": "Description of what becomes possible.",
      "tip": "How to get started with this workflow today.",
      "prompt": "A copyable prompt to try this workflow."
    }
  ],
  "fun_ending": {
    "headline": "A witty one-liner about a memorable moment from the sessions.",
    "detail": "A brief, fun description of something notable that happened in the data."
  },
  "feedback": {
    "intro": "Optional intro text for the team feedback section.",
    "team": [
      {
        "title": "Observation title",
        "detail": "Detailed feedback about team interactions observed in the sessions.",
        "evidence": "Supporting evidence from session data."
      }
    ],
    "model": [
      {
        "title": "Model observation title",
        "detail": "Observations about model behavior patterns.",
        "evidence": "Supporting evidence."
      }
    ]
  }
}
```

### Narrative Generation Guidelines

When generating narratives:
1. **Be specific** — reference actual session titles, tool counts, agent names, and patterns from the data
2. **Be honest** — if there are friction points, name them clearly
3. **Be actionable** — every recommendation should be something the user can do immediately
4. **Project areas** — group sessions by topic/project based on their titles and first user messages
5. **Wins** — identify 2-4 genuinely impressive accomplishments from the session data
6. **Friction** — identify 2-3 categories of problems that recurred
7. **What you wanted** — classify each session's primary intent (e.g., "Implement Feature", "Debug Issue", "Information Question", "File Operations", "Setup/Config")
8. **Outcomes** — estimate outcome per session: "Fully Achieved", "Mostly Achieved", "Partially Achieved" based on error counts, session length, and whether the task seemed to complete
9. **Satisfaction** — estimate satisfaction per session: "Likely Satisfied" or "Dissatisfied" based on error rates and session patterns
10. **Features** — recommend OpenCode features that would help based on the data (hooks, custom commands, task agents, AGENTS.md, etc.)
11. **Fun ending** — find the most entertaining or memorable data point
12. **Feedback** — if applicable, generate team/model observations based on multi-agent interactions, coordination patterns, or notable model behavior

### Important Context for Recommendations

This is **OpenCode** (not Claude Code). Available features to recommend:
- **AGENTS.md** — Project-level instructions file (equivalent to CLAUDE.md)
- **Custom Commands** — Reusable prompt templates in `~/.config/opencode/command/` triggered by `/command-name`
- **Hooks** — Not available in OpenCode yet, but can mention as future feature
- **Task Agents** — Multi-agent orchestration via oh-my-opencode (explore, librarian, oracle subagents)
- **MCP Servers** — External tool integrations (Playwright, Context7, vibe-kanban, etc.)
- **Session Tools** — session_list, session_read, session_search for reviewing past work

## Step 3: Merge and Generate Report

Merge the raw metrics and narratives into a single report data file:

```python
import json

metrics = json.load(open('{{INSIGHTS_HOME}}/output/raw_metrics.json'))
narratives = json.load(open('{{INSIGHTS_HOME}}/output/narratives.json'))

report_data = {
    "metrics": metrics,
    "narratives": narratives
}

with open('{{INSIGHTS_HOME}}/output/report_data.json', 'w') as f:
    json.dump(report_data, f, indent=2, ensure_ascii=False)
```

Then generate the HTML report:

```bash
python3 {{INSIGHTS_HOME}}/src/generator.py --input {{INSIGHTS_HOME}}/output/report_data.json --output {{INSIGHTS_HOME}}/output/report.html
```

## Step 4: Present Results

Tell the user:
1. The report has been generated at `output/report.html`
2. Summarize the key findings from the At a Glance section
3. Mention the top 2-3 recommendations

The user can open the HTML file in a browser to see the full interactive report.

## Error Handling

- If the collector returns "No sessions found", suggest using `--days 30` or omitting the days filter
- If the generator fails, check that all required narrative fields are present in the JSON
- If a narrative field is missing data, use reasonable defaults rather than failing
