"""Conservative date normalization, anchored to the meeting's explicit date."""
from __future__ import annotations
from datetime import date, timedelta
import re

DAYS = {name:i for i,name in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])}


def resolve_due(phrase: str, meeting_date: str) -> dict:
    """Unknown and ambiguous dates remain unresolved rather than invented.

    A bare weekday means the nearest matching day on or after the meeting.
    `next weekday` means strictly after it. Deadlines are all-day calendar dates.
    """
    raw = phrase.strip().strip('.;,')
    value = re.sub(r'^(?:by|due(?: on)?|before|on)\s+', '', raw, flags=re.I).strip().lower()
    anchor = date.fromisoformat(meeting_date)
    def shift(days: int):
        try:return anchor+timedelta(days=days)
        except OverflowError:return None
    result = None
    rule = 'unresolved'
    if not value:return {'raw':raw,'date':None,'rule':'not_stated','warning':'No deadline stated'}
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        try:result = date.fromisoformat(value);rule='iso_date'
        except ValueError:pass
    elif value in {'today','tomorrow'}:
        result=shift(int(value=='tomorrow'));rule='relative_day'
    elif re.fullmatch(r'in \d{1,3} days?', value):
        count=int(value.split()[1])
        if count <= 365:result=shift(count);rule='relative_days'
    elif re.fullmatch(r'(?:next )?(?:'+'|'.join(DAYS)+')', value):
        day=value.removeprefix('next ');delta=(DAYS[day]-anchor.weekday())%7
        if value.startswith('next ') and delta==0:delta=7
        result=shift(delta);rule='weekday'
    warning = None
    if result is None:warning='Ambiguous or unsupported deadline; human confirmation required'
    elif result < anchor:warning='Deadline precedes the meeting date'
    return {'raw':raw,'date':result.isoformat() if result else None,'rule':rule,'warning':warning}


def deadline_from_text(text: str, meeting_date: str) -> dict:
    match = re.search(r'\b(?:by|due(?: on)?)\s+(.+?)(?=[;.!?]|$)', text, re.I)
    return resolve_due(match.group(1) if match else '', meeting_date)
