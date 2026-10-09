"""Explainable English transcript heuristics with exact source citations.

Candidates are proposals, never approved facts. Each rule is deliberately narrow;
implicit commitments, sarcasm and negation require human review.
"""
from __future__ import annotations
import re
from app.domain.transcript import citation
from app.domain.deadlines import deadline_from_text

RULE_VERSION='1.0.0'
ACTION = re.compile(r'^(?:action|todo)\s*:\s*(.+)$',re.I)
COMMIT = re.compile(r"\b(?:I (?:will|shall)|I'll|I commit to)\s+(.+)",re.I)
DECISION = re.compile(r'^(?:decision|decided|agreed)\s*:\s*(.+)$',re.I)
DECIDED = re.compile(r'\b(?:we decided to|we agreed to|the decision is to)\s+(.+)',re.I)
QUESTION = re.compile(r'^(?:question|open question)\s*:\s*(.+)$',re.I)
NEGATION = re.compile(r"\b(?:not|never|won't|cannot|can't|unless|if|might|maybe)\b",re.I)


def named_owner(text: str, participants: list[str]) -> str | None:
    for name in sorted(participants,key=len,reverse=True):
        pattern = r'^'+re.escape(name)+r'(?:\s*[-–:]\s*|\s+(?:will|to|shall)\s+)'
        if re.search(pattern,text,re.I):return name
    return None


def extract(meeting: dict) -> dict:
    document=meeting['document'];out=[];seen=set()
    for turn in document['turns']:
        text=turn['text'];kind=None;body='';rule='';owner=None
        match=ACTION.match(text)
        if match:
            kind='action';body=match.group(1);rule='explicit_action'
            owner=named_owner(body,meeting['participants'])
        elif (match:=COMMIT.search(text)):
            kind='action';body=match.group(1);rule='speaker_commitment';owner=turn['speaker']
        elif (match:=DECISION.match(text)) or (match:=DECIDED.search(text)):
            kind='decision';body=match.group(1);rule='explicit_decision'
        elif (match:=QUESTION.match(text)):
            kind='question';body=match.group(1);rule='explicit_question'
        elif text.endswith('?'):
            kind='question';body=text;rule='question_mark'
        if kind is None:continue
        # Preserve meaningful wording, including negatives; flag rather than rewrite.
        body=body.strip()
        if not body:continue
        fingerprint=(kind,body.casefold(),owner)
        if fingerprint in seen:continue
        seen.add(fingerprint)
        flags=[]
        if NEGATION.search(text):flags.append('conditional_or_negative')
        if kind=='action' and owner is None:flags.append('owner_unresolved')
        due=deadline_from_text(body,meeting['meeting_date']) if kind=='action' else {'raw':'','date':None,'rule':'not_applicable','warning':None}
        if kind=='action' and due['warning']:flags.append('deadline_unresolved' if not due['date'] else 'deadline_before_meeting')
        evidence=citation(document,turn['id'],text)
        out.append({'id':f'p{len(out)+1:04d}','kind':kind,'text':body,'owner':owner,
                    'due':due,'evidence':[evidence],'rule':rule,'flags':flags,'source':'rules',
                    'confidence_label':'explicit cue' if rule.startswith('explicit') else 'heuristic cue'})
        if len(out)>=200:break
    return {'rule_version':RULE_VERSION,'proposals':out,
            'warnings':['Candidates require review; unresolved owners and dates are intentionally left blank.']+
                       (['Proposal limit reached; inspect the remaining transcript manually.'] if len(out)>=200 else [])}


def meeting_digest(meeting: dict, items: list[dict]) -> dict:
    counts={kind:sum(i['kind']==kind for i in items) for kind in ['action','decision','question']}
    actions=[i for i in items if i['kind']=='action']
    return {'title':meeting['title'],'counts':counts,'unassigned_actions':sum(not i.get('owner') for i in actions),
            'undated_actions':sum(not i.get('due_date') for i in actions),
            'done_actions':sum(i.get('status')=='done' for i in actions),
            'open_questions':sum(i['kind']=='question' and i.get('status')!='resolved' for i in items),
            'speakers':sorted({t['speaker'] for t in meeting['document']['turns'] if t['speaker']}),
            'source_turns':len(meeting['document']['turns'])}
