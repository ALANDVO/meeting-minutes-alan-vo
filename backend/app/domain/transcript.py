"""Bounded transcript ingestion with stable, verifiable source references.

This accepts text transcripts; it does not transcribe audio or infer identities.
Offsets refer to the stored normalized UTF-8 text after CRLF normalization.
"""
from __future__ import annotations

from datetime import date
import hashlib
import re
import unicodedata
from app.core.errors import AppError

MAX_TRANSCRIPT = 100_000
MAX_TURNS = 1000
MAX_PARTICIPANTS = 50
KINDS = {'standup', 'design_review', 'one_on_one', 'planning', 'retrospective', 'general'}
PREFIX = re.compile(r'^(?:\[(?P<time>\d{1,2}:\d{2}(?::\d{2})?)\]\s*)?(?P<speaker>[^:\n]{1,80}):\s*(?P<body>.*)$')
RESERVED = {'action', 'decision', 'question', 'todo', 'note', 'owner', 'due', 'agenda', 'topic'}


def fail(message: str, code: str = 'invalid_transcript') -> None:
    raise AppError(422, code, message)


def clean_text(value: object, name: str, limit: int, *, multiline: bool = False, empty: bool = False) -> str:
    if not isinstance(value, str):fail(f'{name} must be text')
    if len(value) > limit:fail(f'{name} exceeds {limit} characters')
    try:value.encode('utf-8')
    except UnicodeEncodeError:fail(f'{name} contains invalid Unicode')
    if any(unicodedata.category(c) in {'Cc', 'Cs'} and not (multiline and c in '\n\r\t') for c in value):
        fail(f'{name} contains control characters')
    value = value.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not empty and not value:fail(f'{name} must not be empty')
    return value


def iso_date(value: object, name: str = 'meeting_date') -> str:
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):fail(f'{name} must be YYYY-MM-DD')
    try:return date.fromisoformat(value).isoformat()
    except ValueError:fail(f'{name} is not a valid date')


def roster(raw: object) -> list[str]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_PARTICIPANTS:
        fail(f'participants must contain 1–{MAX_PARTICIPANTS} names')
    names = [clean_text(n, 'participant', 80) for n in raw]
    keys = [n.casefold() for n in names]
    if len(set(keys)) != len(keys):fail('Participant names must be unique ignoring case')
    if any(':' in n or '\n' in n for n in names):fail('Participant names must not contain colons')
    return names


def parse_transcript(raw: object, participants: list[str]) -> dict:
    text = clean_text(raw, 'transcript', MAX_TRANSCRIPT, multiline=True)
    names = {p.casefold(): p for p in participants}
    turns: list[dict] = []
    offset = 0
    for line_no, line in enumerate(text.splitlines(keepends=True), 1):
        content = line.rstrip('\n')
        if not content.strip():offset += len(line);continue
        match = PREFIX.match(content)
        speaker = None
        timestamp = None
        body = content.strip()
        body_start = offset + len(content) - len(content.lstrip())
        if match and match['speaker'].strip().casefold() not in RESERVED:
            candidate = match['speaker'].strip()
            # Unknown speakers remain explicit unknowns; never resolve by fuzzy matching.
            speaker = names.get(candidate.casefold())
            timestamp = match['time']
            body = match['body'].strip()
            body_start = offset + match.start('body') + len(match['body']) - len(match['body'].lstrip())
            raw_speaker = candidate
        else:raw_speaker = None
        if len(body) > 4000:fail('A transcript turn exceeds 4000 characters; split it into shorter lines')
        if body:
            turns.append({'id':f't{len(turns)+1:04d}', 'line':line_no, 'speaker':speaker,
                          'raw_speaker':raw_speaker,'timestamp':timestamp, 'text':body,
                          'start':body_start,'end':body_start+len(body)})
        if len(turns) > MAX_TURNS:fail(f'Transcript exceeds {MAX_TURNS} nonempty turns')
        offset += len(line)
    if not turns:fail('Transcript has no spoken text')
    digest = hashlib.sha256(text.encode()).hexdigest()
    return {'text':text,'sha256':digest,'turns':turns,'characters':len(text),
            'word_count':len(text.split()), 'unknown_speakers':sorted({t['raw_speaker'] for t in turns if t['raw_speaker'] and not t['speaker']})}


def citation(document: dict, turn_id: str, quote: str) -> dict:
    turn = next((t for t in document['turns'] if t['id'] == turn_id), None)
    if turn is None:fail('Citation references an unknown turn', 'invalid_citation')
    quote = clean_text(quote, 'quote', 4000, multiline=True)
    position = turn['text'].find(quote)
    if position < 0:fail('Citation quote is not an exact substring of the referenced turn', 'invalid_citation')
    return {'turn_id':turn_id,'quote':quote,'start':turn['start']+position,
            'end':turn['start']+position+len(quote),'speaker':turn['speaker'],'line':turn['line']}


def prepare_meeting(payload: dict) -> dict:
    if not isinstance(payload, dict):fail('Meeting must be a JSON object')
    names = roster(payload.get('participants'))
    kind = payload.get('kind', 'general')
    if not isinstance(kind,str) or kind not in KINDS:fail('Unsupported meeting kind')
    return {'title':clean_text(payload.get('title'), 'title', 160),
            'meeting_date':iso_date(payload.get('meeting_date')),
            'participants':names, 'kind':kind,
            'document':parse_transcript(payload.get('transcript'), names)}
