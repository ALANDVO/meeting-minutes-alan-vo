"""Human corrections and action state transitions with validated provenance."""
from __future__ import annotations
from app.core.errors import AppError
from app.domain.transcript import clean_text, iso_date, citation, fail

STATUSES={'action':{'open','in_progress','blocked','done','cancelled'},
          'decision':{'recorded','superseded'},'question':{'open','resolved'}}
TRANSITIONS={'open':{'in_progress','blocked','done','cancelled'},
             'in_progress':{'open','blocked','done','cancelled'},
             'blocked':{'open','in_progress','done','cancelled'},
             'done':{'open'},'cancelled':{'open'}}


def normalize_item(payload: dict, meeting: dict) -> dict:
    if not isinstance(payload,dict):fail('Item must be an object')
    kind=payload.get('kind')
    if not isinstance(kind,str) or kind not in STATUSES:fail('Item kind must be action, decision or question')
    text=clean_text(payload.get('text'),'item text',4000,multiline=True)
    owner=payload.get('owner') or None
    if owner is not None and owner not in meeting['participants']:fail('Owner must be an exact participant name')
    due=payload.get('due_date') or None
    if due is not None:due=iso_date(due,'due_date')
    if kind!='action' and (owner or due):fail('Only actions have owners and deadlines')
    status=payload.get('status','recorded' if kind=='decision' else 'open')
    if not isinstance(status,str) or status not in STATUSES[kind]:fail('Status is invalid for this item kind')
    evidence=payload.get('evidence')
    if not isinstance(evidence,list) or not 1<=len(evidence)<=8:fail('Every item needs 1–8 exact source citations')
    references=[]
    for entry in evidence:
        if not isinstance(entry,dict):fail('Each citation must be an object')
        ref=citation(meeting['document'],entry.get('turn_id'),entry.get('quote'))
        if ref not in references:references.append(ref)
    return {'kind':kind,'text':text,'owner':owner,'due_date':due,'status':status,
            'evidence':references,'note':clean_text(payload.get('note',''),'note',2000,multiline=True,empty=True)}


def proposal_item(proposal: dict, meeting: dict) -> dict:
    return normalize_item({'kind':proposal['kind'],'text':proposal['text'],
                           'owner':proposal['owner'],'due_date':proposal['due']['date'],
                           'evidence':proposal['evidence'],
                           'note':'Review flags: '+', '.join(proposal['flags']) if proposal['flags'] else ''},meeting)


def validate_transition(item: dict, status: str, reason: str) -> str:
    if item['kind']!='action':raise AppError(409,'not_action','Use item editing for questions and decisions')
    if not isinstance(status,str) or status not in TRANSITIONS.get(item['status'],set()):
        raise AppError(409,'invalid_transition',f"Cannot change {item['status']} to {status}")
    if status in {'done','cancelled'} and not item.get('owner'):
        raise AppError(409,'owner_required','Assign an owner before closing an action')
    return clean_text(reason,'transition reason',1000,multiline=True)


def review_findings(meeting: dict) -> list[dict]:
    findings=[]
    if not meeting.get('items'):findings.append({'severity':'blocking','code':'no_items','message':'Add at least one sourced item before submitting minutes.'})
    for item in meeting.get('items',[]):
        if item['kind']=='action':
            if not item.get('owner'):findings.append({'severity':'warning','code':'unassigned','item_id':item['id'],'message':'Action has no assigned participant.'})
            if not item.get('due_date'):findings.append({'severity':'warning','code':'undated','item_id':item['id'],'message':'Action has no confirmed deadline.'})
            elif item['due_date']<meeting['meeting_date']:findings.append({'severity':'warning','code':'past_due','item_id':item['id'],'message':'Deadline is earlier than the meeting date.'})
    if meeting['document'].get('unknown_speakers'):
        findings.append({'severity':'warning','code':'unknown_speakers','message':'Some transcript labels do not match the participant roster.'})
    return findings
