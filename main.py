#!/usr/bin/env python3
# meeting-minutes — AI meeting transcription and summarization tool that extracts action items, decisions, owners, and deadlines from raw meeting text, then generates Slack-ready summaries and calendar follow-ups.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
def _load_transcript(args):
    if getattr(args, "stdin", False):
        return sys.stdin.read()
    with open(args.file) as f:
        return f.read()

def minutes(args):
    """Generate structured meeting minutes from a transcript."""
    llm = LLM()
    text = _load_transcript(args)
    print(f"Processing {len(text.split())} words...\n")

    meeting_type = llm.classify(
        text=text[:3000],
        categories=["standup", "design_review", "one_on_one", "planning", "retrospective", "status_update", "general"],
        instructions="Classify the type of meeting based on the content, participants, and topics discussed."
    )
    mtype = meeting_type.get("category", "general")
    print(f"Detected meeting type: {mtype}")

    result = llm.generate(
        f"Meeting transcript ({mtype}):\n\n{text}\n\n"
        "Produce structured meeting minutes in Markdown with these EXACT sections:\n"
        "## Summary (3-5 sentences, what this meeting accomplished)\n"
        "## Decisions (each with: decision, rationale, decided-by) — use a numbered list\n"
        "## Action Items (each with: task, owner, deadline, status: new|existing) — use a table with columns | # | Task | Owner | Deadline |\n"
        "## Open Questions (unresolved items needing follow-up)\n"
        "## Key Discussion Points (topics with 1-2 sentence summaries of conclusions)\n"
        "## Next Meeting (suggested agenda if applicable)\n\n"
        "Be faithful to the transcript. Do not invent owners or deadlines that were not stated — mark them as 'TBD' if missing.",
        system="You are a meticulous executive assistant. Extract facts precisely. Attribute every action item to a named owner from the transcript. Preserve deadlines exactly as stated."
    )

    print(result)
    if args.output:
        with open(args.output, "w") as f:
            f.write(f"# Meeting Minutes — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n**Type:** {mtype}\n\n{result}\n")
        print(f"\nSaved to {args.output}")
    return result

def actions(args):
    """Extract and track action items with assignments."""
    llm = LLM()
    text = _load_transcript(args)
    print(f"Extracting action items from {len(text.split())} words...\n")

    result = llm.generate(
        f"Meeting transcript:\n\n{text}\n\n"
        "Extract ALL action items (explicit or implicit commitments like 'I will handle that', 'let us schedule that', 'can you look into this?'). "
        "For each item provide: task description, owner (full name as spoken in transcript), deadline (as stated, or 'none'), priority (high|medium|low based on context), and a suggested concrete next step. "
        "Output as a JSON array. Each object: {\"task\": \"...\", \"owner\": \"...\", \"deadline\": \"...\", \"priority\": \"...\", \"next_step\": \"...\"}",
        system="You extract commitments from meetings. An action item exists whenever someone says they will do something, or when the group assigns a task. Be thorough — miss nothing."
    )

    items = _parse_json_array(result)
    if not items:
        print("No action items found, or parse failed:")
        print(result[:500])
        return []

    print(f"{'='*60}")
    print(f"ACTION ITEMS: {len(items)}")
    print(f"{'='*60}")
    for i, item in enumerate(items, 1):
        prio_icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(item.get("priority", "medium"), "⚪")
        print(f"\n  {i}. {prio_icon} [{item.get('priority', '?').upper()}] {item.get('task', '?')}")
        print(f"     Owner:    {item.get('owner', 'TBD')}")
        print(f"     Deadline: {item.get('deadline', 'none')}")
        if item.get("next_step"):
            print(f"     Next:     {item['next_step']}")

    owners = Counter(item.get("owner", "TBD") for item in items)
    print(f"\n  BY OWNER:")
    for owner, count in owners.most_common():
        print(f"    {owner}: {count} item(s)")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(items, f, indent=2)
        print(f"\nSaved to {args.output}")
    return items

def slack(args):
    """Generate a Slack-ready meeting summary."""
    llm = LLM()
    text = _load_transcript(args)
    channel = args.channel or "#general"
    print(f"Generating Slack summary for {channel}...\n")

    summary = llm.generate(
        f"Meeting transcript:\n\n{text}\n\n"
        "Write a Slack message summarizing this meeting. Format requirements:\n"
        "- Start with an emoji that fits the meeting type + a one-line headline\n"
        "- Use *bold* for section labels: *Decisions*, *Action Items*, *Follow-ups*\n"
        "- Action items as bullet points with @owner mentions (first name only)\n"
        "- Keep it scannable: max 15 lines total\n"
        "- End with a suggested next-checkin time if relevant\n"
        "- No markdown headers (Slack does not use #), no tables\n"
        "Output ONLY the Slack message, ready to paste.",
        system="You write Slack updates that busy engineers actually read. Punchy, specific, zero fluff."
    )

    print(f"{'='*60}")
    print(f"SLACK MESSAGE")
    print(f"{'='*60}")
    print(summary)

    if args.output:
        with open(args.output, "w") as f:
            f.write(summary)
        print(f"\nSaved to {args.output}")
    return summary

def followups(args):
    """Generate calendar follow-up suggestions."""
    llm = LLM()
    text = _load_transcript(args)
    start = args.start_date or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Generating follow-ups (starting {start})...\n")

    result = llm.generate(
        f"Meeting transcript:\n\n{text}\n\n"
        f"Generate calendar follow-up suggestions. Today is {start}. For each follow-up needed, output a JSON object: "
        "{\"title\": \"...\", \"attendees\": [\"name\", ...], \"suggested_date\": \"YYYY-MM-DD\", \"duration_minutes\": 30, \"description\": \"agenda in 3 bullets\"}\n"
        "Rules: schedule within 2 weeks; standup-type followups within 1 day; design reviews 3-5 days out; include only attendees mentioned in the transcript. "
        "Output a JSON array.",
        system="You schedule follow-ups the way a great PM does: right timing, right people, tight agenda. Never schedule more than necessary."
    )

    followups = _parse_json_array(result)
    if not followups:
        print("No follow-ups suggested, or parse failed:")
        print(result[:500])
        return []

    print(f"{'='*60}")
    print(f"FOLLOW-UP SCHEDULE: {len(followups)}")
    print(f"{'='*60}")
    for i, fu in enumerate(followups, 1):
        print(f"\n  {i}. {fu.get('title', '?')}")
        print(f"     When:      {fu.get('suggested_date', '?')} ({fu.get('duration_minutes', 30)} min)")
        print(f"     Attendees: {', '.join(fu.get('attendees', []))}")
        if fu.get("description"):
            for line in fu["description"].split("\n"):
                if line.strip():
                    print(f"       {line.strip()}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(followups, f, indent=2)
        print(f"\nSaved to {args.output}")
    return followups

def _parse_json_array(raw):
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(raw[start:end + 1])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

def main():
    import argparse
    p = argparse.ArgumentParser(prog="meeting-minutes", description="AI meeting minutes and action item extraction")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("minutes", help="Generate structured meeting minutes")
    m.add_argument("--file", default=None); m.add_argument("--stdin", action="store_true"); m.add_argument("--output", default=None)
    m.set_defaults(fn=minutes)

    a = sub.add_parser("actions", help="Extract action items with owners and deadlines")
    a.add_argument("--file", default=None); a.add_argument("--stdin", action="store_true")
    a.add_argument("--assign", action="store_true"); a.add_argument("--output", default=None)
    a.set_defaults(fn=actions)

    s = sub.add_parser("slack", help="Generate a Slack-ready summary")
    s.add_argument("--file", default=None); s.add_argument("--stdin", action="store_true")
    s.add_argument("--channel", default=None); s.add_argument("--output", default=None)
    s.set_defaults(fn=slack)

    f = sub.add_parser("followups", help="Generate calendar follow-up suggestions")
    f.add_argument("--file", default=None); f.add_argument("--stdin", action="store_true")
    f.add_argument("--start-date", default=None); f.add_argument("--output", default=None)
    f.set_defaults(fn=followups)

    args = p.parse_args()
    if not args.file and not getattr(args, "stdin", False):
        p.error("provide --file or --stdin")
    args.fn(args)

if __name__ == '__main__':
    main()
