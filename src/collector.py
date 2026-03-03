#!/usr/bin/env python3
"""
OpenCode Insights Collector
Extracts session metrics from OpenCode's SQLite database.
Outputs a structured JSON with all quantitative data needed for report generation.
"""

import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Default DB path
DEFAULT_DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")

# File extension → language mapping
EXT_TO_LANG = {
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".js": "JavaScript",
    ".jsx": "JSX",
    ".py": "Python",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".swift": "Swift",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".dockerfile": "Dockerfile",
    ".xml": "XML",
    ".graphql": "GraphQL",
    ".proto": "Protobuf",
    ".lua": "Lua",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".zig": "Zig",
    ".nim": "Nim",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


def connect_db(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_sessions(
    conn: sqlite3.Connection,
    project_id: str | None = None,
    days: int | None = None,
    exclude_subagent: bool = True,
) -> list[dict]:
    """Fetch sessions with optional filters."""
    query = "SELECT * FROM session WHERE 1=1"
    params: list[Any] = []

    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)

    if days:
        cutoff = int((datetime.now(timezone.utc).timestamp() - days * 86400) * 1000)
        query += " AND time_created >= ?"
        params.append(cutoff)

    if exclude_subagent:
        query += " AND title NOT LIKE '%subagent%'"

    query += " ORDER BY time_created ASC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_messages_for_sessions(
    conn: sqlite3.Connection, session_ids: list[str]
) -> list[dict]:
    """Fetch all messages for given sessions."""
    if not session_ids:
        return []
    placeholders = ",".join("?" * len(session_ids))
    rows = conn.execute(
        f"SELECT * FROM message WHERE session_id IN ({placeholders}) ORDER BY time_created ASC",
        session_ids,
    ).fetchall()
    return [dict(r) for r in rows]


def get_parts_for_sessions(
    conn: sqlite3.Connection, session_ids: list[str]
) -> list[dict]:
    """Fetch all parts for given sessions."""
    if not session_ids:
        return []
    placeholders = ",".join("?" * len(session_ids))
    rows = conn.execute(
        f"SELECT * FROM part WHERE session_id IN ({placeholders}) ORDER BY time_created ASC",
        session_ids,
    ).fetchall()
    return [dict(r) for r in rows]


def get_todos_for_sessions(
    conn: sqlite3.Connection, session_ids: list[str]
) -> list[dict]:
    """Fetch all todos for given sessions."""
    if not session_ids:
        return []
    placeholders = ",".join("?" * len(session_ids))
    rows = conn.execute(
        f"SELECT * FROM todo WHERE session_id IN ({placeholders})",
        session_ids,
    ).fetchall()
    return [dict(r) for r in rows]


def parse_json_field(raw: str) -> dict:
    """Safely parse a JSON string field."""
    try:
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def compute_session_metrics(sessions: list[dict]) -> dict:
    """Compute aggregate session-level metrics."""
    total = len(sessions)
    if total == 0:
        return {"total_sessions": 0}

    timestamps = [s["time_created"] for s in sessions]
    start_ts = min(timestamps)
    end_ts = max(max(s["time_updated"] for s in sessions), max(timestamps))

    start_date = datetime.fromtimestamp(start_ts / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d"
    )
    end_date = datetime.fromtimestamp(end_ts / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d"
    )

    # Active days
    active_days = len(
        set(
            datetime.fromtimestamp(s["time_created"] / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
            for s in sessions
        )
    )

    # Lines and files
    total_additions = sum(s.get("summary_additions") or 0 for s in sessions)
    total_deletions = sum(s.get("summary_deletions") or 0 for s in sessions)
    total_files = sum(s.get("summary_files") or 0 for s in sessions)

    # Per-session details for AI analysis
    session_details = []
    for s in sessions:
        duration_ms = (s["time_updated"] or s["time_created"]) - s["time_created"]
        session_details.append(
            {
                "id": s["id"],
                "title": s["title"],
                "directory": s.get("directory", ""),
                "time_created": s["time_created"],
                "time_updated": s["time_updated"],
                "duration_minutes": round(duration_ms / 60000, 1),
                "additions": s.get("summary_additions") or 0,
                "deletions": s.get("summary_deletions") or 0,
                "files_changed": s.get("summary_files") or 0,
            }
        )

    return {
        "total_sessions": total,
        "date_range": {"start": start_date, "end": end_date},
        "active_days": active_days,
        "lines": {"added": total_additions, "deleted": total_deletions},
        "total_files_changed": total_files,
        "session_details": session_details,
    }


def compute_message_metrics(messages: list[dict]) -> dict:
    """Compute message-level metrics."""
    total = len(messages)
    if total == 0:
        return {"total_messages": 0}

    role_counts: Counter = Counter()
    agent_counts: Counter = Counter()
    model_counts: Counter = Counter()
    user_message_times: list[int] = []
    hour_counts: Counter = Counter()
    response_times: list[float] = []

    # Token tracking
    total_input_tokens = 0
    total_output_tokens = 0
    total_reasoning_tokens = 0
    total_cache_read = 0
    total_cache_write = 0
    total_cost = 0.0

    # Group messages by session for response time calculation
    session_messages: dict[str, list[dict]] = defaultdict(list)

    for msg in messages:
        data = parse_json_field(msg["data"])
        role = data.get("role", "unknown")
        role_counts[role] += 1

        agent = data.get("agent", "unknown")
        agent_counts[agent] += 1

        if role == "assistant":
            model_id = data.get("modelID") or data.get("model", {}).get(
                "modelID", "unknown"
            )
            model_counts[model_id] += 1

            tokens = data.get("tokens", {})
            total_input_tokens += tokens.get("input", 0)
            total_output_tokens += tokens.get("output", 0)
            total_reasoning_tokens += tokens.get("reasoning", 0)
            cache = tokens.get("cache", {})
            total_cache_read += cache.get("read", 0)
            total_cache_write += cache.get("write", 0)
            total_cost += data.get("cost", 0)

        if role == "user":
            ts = msg["time_created"]
            user_message_times.append(ts)
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            hour_counts[dt.hour] += 1

        session_messages[msg["session_id"]].append(
            {"role": role, "time_created": msg["time_created"], "data": data}
        )

    # Compute response times (time between user msg and next assistant msg)
    for session_id, msgs in session_messages.items():
        for i in range(len(msgs) - 1):
            if msgs[i]["role"] == "user" and msgs[i + 1]["role"] == "assistant":
                time_data = msgs[i + 1]["data"].get("time", {})
                completed = time_data.get("completed", msgs[i + 1]["time_created"])
                created = time_data.get("created", msgs[i + 1]["time_created"])
                # Response time = assistant completion - user creation
                rt = (completed - msgs[i]["time_created"]) / 1000  # seconds
                if 0 < rt < 3600:  # sanity check: 0 to 60 minutes
                    response_times.append(rt)

    # User response times (time between assistant completion and next user msg)
    user_response_times: list[float] = []
    for session_id, msgs in session_messages.items():
        for i in range(len(msgs) - 1):
            if msgs[i]["role"] == "assistant" and msgs[i + 1]["role"] == "user":
                time_data = msgs[i]["data"].get("time", {})
                completed = time_data.get("completed", msgs[i]["time_created"])
                user_ts = msgs[i + 1]["time_created"]
                urt = (user_ts - completed) / 1000
                if 0 < urt < 7200:
                    user_response_times.append(urt)

    # Response time distribution buckets
    def bucket_times(times: list[float]) -> list[dict]:
        buckets = [
            ("< 2s", 0, 2),
            ("2-10s", 2, 10),
            ("10-30s", 10, 30),
            ("30s-1m", 30, 60),
            ("1-2m", 60, 120),
            ("2-5m", 120, 300),
            ("5-15m", 300, 900),
            (">15m", 900, float("inf")),
        ]
        result = []
        for label, lo, hi in buckets:
            count = sum(1 for t in times if lo <= t < hi)
            if count > 0:
                result.append({"name": label, "count": count})
        return result

    # Compute messages per day
    if user_message_times:
        days_span = max(
            1,
            (max(user_message_times) - min(user_message_times)) / (86400 * 1000),
        )
        msgs_per_day = round(role_counts.get("user", 0) / max(days_span, 1), 1)
    else:
        msgs_per_day = 0

    # Per-session message counts for session type classification
    session_msg_counts: dict[str, int] = Counter()
    for msg in messages:
        data = parse_json_field(msg["data"])
        if data.get("role") == "user":
            session_msg_counts[msg["session_id"]] += 1

    # Session type classification
    session_types: Counter = Counter()
    for sid, count in session_msg_counts.items():
        if count <= 2:
            session_types["Quick Question"] += 1
        elif count <= 5:
            session_types["Single Task"] += 1
        elif count <= 10:
            session_types["Multi Task"] += 1
        elif count <= 20:
            session_types["Iterative Refinement"] += 1
        else:
            session_types["Exploration"] += 1

    return {
        "total_messages": total,
        "user_messages": role_counts.get("user", 0),
        "assistant_messages": role_counts.get("assistant", 0),
        "messages_per_day": msgs_per_day,
        "agent_distribution": [
            {"name": name, "count": count}
            for name, count in agent_counts.most_common()
            if name != "unknown" and name != "compaction"
        ],
        "model_distribution": [
            {"name": name, "count": count}
            for name, count in model_counts.most_common()
            if name != "unknown"
        ],
        "hour_distribution": {str(h): hour_counts.get(h, 0) for h in range(24)},
        "user_response_time": {
            "median": round(
                sorted(user_response_times)[len(user_response_times) // 2], 1
            )
            if user_response_times
            else 0,
            "average": round(sum(user_response_times) / len(user_response_times), 1)
            if user_response_times
            else 0,
            "distribution": bucket_times(user_response_times),
        },
        "assistant_response_time": {
            "median": round(sorted(response_times)[len(response_times) // 2], 1)
            if response_times
            else 0,
            "average": round(sum(response_times) / len(response_times), 1)
            if response_times
            else 0,
            "distribution": bucket_times(response_times),
        },
        "session_types": [
            {"name": name, "count": count}
            for name, count in session_types.most_common()
        ],
        "tokens": {
            "total_input": total_input_tokens,
            "total_output": total_output_tokens,
            "total_reasoning": total_reasoning_tokens,
            "total_cache_read": total_cache_read,
            "total_cache_write": total_cache_write,
        },
        "total_cost": round(total_cost, 4),
    }


def compute_tool_metrics(parts: list[dict]) -> dict:
    """Compute tool usage metrics from parts."""
    tool_counts: Counter = Counter()
    tool_errors: Counter = Counter()
    file_paths: list[str] = []

    for part in parts:
        data = parse_json_field(part["data"])
        if data.get("type") != "tool":
            continue

        tool_name = data.get("tool", "unknown")
        state = data.get("state", {})
        status = state.get("status", "")

        tool_counts[tool_name] += 1

        # Track errors
        if status == "error":
            tool_errors["Other"] += 1
        elif status == "completed":
            metadata = state.get("metadata", {})
            exit_code = metadata.get("exit")
            if exit_code and exit_code != 0:
                tool_errors["Command Failed"] += 1
        elif status == "rejected":
            tool_errors["User Rejected"] += 1

        # Extract file paths for language detection
        input_data = state.get("input", {})
        for key in ("filePath", "file_path", "path", "pattern"):
            val = input_data.get(key, "")
            if isinstance(val, str) and val:
                file_paths.append(val)

        # Also check output for file paths (from glob, grep)
        output = state.get("output", "")
        if isinstance(output, str):
            for line in output.split("\n"):
                line = line.strip()
                if line and "." in line and "/" in line and len(line) < 300:
                    file_paths.append(line)

    # Language detection from file paths
    lang_counts: Counter = Counter()
    seen_files: set = set()
    for fp in file_paths:
        # Clean path
        fp = fp.strip()
        if not fp or fp in seen_files:
            continue
        seen_files.add(fp)

        ext = Path(fp).suffix.lower()
        lang = EXT_TO_LANG.get(ext)
        if lang:
            lang_counts[lang] += 1

    return {
        "tool_usage": [
            {"name": name, "count": count} for name, count in tool_counts.most_common()
        ],
        "tool_errors": [
            {"name": name, "count": count} for name, count in tool_errors.most_common()
        ],
        "languages": [
            {"name": name, "count": count} for name, count in lang_counts.most_common()
        ],
    }


def detect_multi_clauding(sessions: list[dict]) -> dict:
    """Detect overlapping sessions (multi-clauding)."""
    overlap_events = 0
    sessions_involved: set = set()

    # Sort by start time
    sorted_sessions = sorted(sessions, key=lambda s: s["time_created"])

    for i, s1 in enumerate(sorted_sessions):
        s1_start = s1["time_created"]
        s1_end = s1["time_updated"] or s1_start

        for j in range(i + 1, len(sorted_sessions)):
            s2 = sorted_sessions[j]
            s2_start = s2["time_created"]

            if s2_start > s1_end:
                break

            # s2 starts before s1 ends → overlap
            overlap_events += 1
            sessions_involved.add(s1["id"])
            sessions_involved.add(s2["id"])

    pct = round(len(sessions_involved) / len(sessions) * 100) if sessions else 0
    return {
        "overlap_events": overlap_events,
        "sessions_involved": len(sessions_involved),
        "pct_sessions": pct,
    }


def compute_todo_metrics(todos: list[dict]) -> dict:
    """Compute todo completion metrics."""
    total = len(todos)
    if total == 0:
        return {"total_todos": 0}

    status_counts: Counter = Counter()
    for t in todos:
        status_counts[t.get("status", "unknown")] += 1

    return {
        "total_todos": total,
        "completed": status_counts.get("completed", 0),
        "in_progress": status_counts.get("in_progress", 0),
        "pending": status_counts.get("pending", 0),
        "cancelled": status_counts.get("cancelled", 0),
        "completion_rate": round(status_counts.get("completed", 0) / total * 100, 1)
        if total > 0
        else 0,
    }


def extract_session_summaries(
    sessions: list[dict],
    messages: list[dict],
    parts: list[dict],
) -> list[dict]:
    """Extract per-session summaries for AI analysis."""
    # Group messages and parts by session
    session_messages: dict[str, list[dict]] = defaultdict(list)
    session_parts: dict[str, list[dict]] = defaultdict(list)

    for msg in messages:
        session_messages[msg["session_id"]].append(msg)
    for part in parts:
        session_parts[part["session_id"]].append(part)

    summaries = []
    for s in sessions:
        sid = s["id"]
        msgs = session_messages.get(sid, [])
        pts = session_parts.get(sid, [])

        # Get first user messages for context
        first_user_texts = []
        for msg in msgs:
            data = parse_json_field(msg["data"])
            if data.get("role") == "user" and len(first_user_texts) < 3:
                # Find text parts for this message
                for p in pts:
                    if p["message_id"] == msg["id"]:
                        pdata = parse_json_field(p["data"])
                        if pdata.get("type") == "text":
                            text = pdata.get("text", "")[:500]
                            if text:
                                first_user_texts.append(text)

        # Count tools used in session
        session_tools: Counter = Counter()
        session_errors = 0
        for p in pts:
            pdata = parse_json_field(p["data"])
            if pdata.get("type") == "tool":
                session_tools[pdata.get("tool", "unknown")] += 1
                state = pdata.get("state", {})
                if state.get("status") in ("error", "rejected"):
                    session_errors += 1
                elif state.get("status") == "completed":
                    meta = state.get("metadata", {})
                    if meta.get("exit") and meta["exit"] != 0:
                        session_errors += 1

        # Count user/assistant messages
        user_msgs = sum(
            1 for m in msgs if parse_json_field(m["data"]).get("role") == "user"
        )
        asst_msgs = sum(
            1 for m in msgs if parse_json_field(m["data"]).get("role") == "assistant"
        )

        # Get agents used
        agents = set()
        for m in msgs:
            data = parse_json_field(m["data"])
            agent = data.get("agent")
            if agent and agent != "compaction":
                agents.add(agent)

        duration_ms = (s["time_updated"] or s["time_created"]) - s["time_created"]

        summaries.append(
            {
                "id": sid,
                "title": s["title"],
                "directory": s.get("directory", ""),
                "duration_minutes": round(duration_ms / 60000, 1),
                "user_messages": user_msgs,
                "assistant_messages": asst_msgs,
                "total_messages": len(msgs),
                "first_user_texts": first_user_texts,
                "tools_used": [
                    {"name": n, "count": c} for n, c in session_tools.most_common(10)
                ],
                "errors": session_errors,
                "agents": list(agents),
                "additions": s.get("summary_additions") or 0,
                "deletions": s.get("summary_deletions") or 0,
                "files_changed": s.get("summary_files") or 0,
                "date": datetime.fromtimestamp(
                    s["time_created"] / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M"),
            }
        )

    return summaries


def get_projects(conn: sqlite3.Connection) -> list[dict]:
    """Get all projects."""
    rows = conn.execute("SELECT * FROM project").fetchall()
    return [dict(r) for r in rows]


def collect(
    db_path: str = DEFAULT_DB_PATH,
    project_id: str | None = None,
    days: int | None = None,
    output_path: str | None = None,
) -> dict:
    """Main collection function. Gathers all metrics from the database."""
    conn = connect_db(db_path)

    try:
        # Get sessions
        sessions = get_sessions(conn, project_id=project_id, days=days)
        if not sessions:
            print("No sessions found matching criteria.", file=sys.stderr)
            return {"error": "No sessions found"}

        session_ids = [s["id"] for s in sessions]

        # Get related data
        messages = get_messages_for_sessions(conn, session_ids)
        parts = get_parts_for_sessions(conn, session_ids)
        todos = get_todos_for_sessions(conn, session_ids)
        projects = get_projects(conn)

        # Compute all metrics
        session_metrics = compute_session_metrics(sessions)
        message_metrics = compute_message_metrics(messages)
        tool_metrics = compute_tool_metrics(parts)
        multi_clauding = detect_multi_clauding(sessions)
        todo_metrics = compute_todo_metrics(todos)
        session_summaries = extract_session_summaries(sessions, messages, parts)

        # Build final output
        result = {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "db_path": db_path,
                "filters": {
                    "project_id": project_id,
                    "days": days,
                },
                "projects": [
                    {"id": p["id"], "name": p.get("name") or p.get("worktree", "")}
                    for p in projects
                ],
            },
            "sessions": session_metrics,
            "messages": message_metrics,
            "tools": tool_metrics,
            "multi_clauding": multi_clauding,
            "todos": todo_metrics,
            "session_summaries": session_summaries,
        }

        # Output
        output_json = json.dumps(result, indent=2, ensure_ascii=False)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"Metrics written to {output_path}", file=sys.stderr)
        else:
            print(output_json)

        return result

    finally:
        conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OpenCode Insights Collector")
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help="Path to OpenCode SQLite database",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Filter by project ID",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Only include sessions from the last N days",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    collect(
        db_path=args.db,
        project_id=args.project,
        days=args.days,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
