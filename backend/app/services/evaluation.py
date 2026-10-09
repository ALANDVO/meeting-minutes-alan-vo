"""Reproducible, deliberately mixed English extraction diagnostic.

Gold labels are manually specified. Results describe this small fixture set, not
accuracy on arbitrary meetings. Difficult implicit/conditional examples remain
in the denominator so the diagnostic exposes the heuristic's limitations.
"""
from app.domain.transcript import prepare_meeting
from app.domain.extraction import extract, RULE_VERSION

CASES=[
    ('explicit action','Alex: ACTION: Sam will document the API by Friday.','action','Sam'),
    ('self commitment','Alex: I will write tests by tomorrow.','action','Alex'),
    ('contraction',"Sam: I'll check the release by Monday.",'action','Sam'),
    ('decision','Alex: Decision: use a queue for ingestion.','decision',None),
    ('agreement','Sam: We agreed to keep the existing API.','decision',None),
    ('question','Alex: Question: Who owns the backlog?','question',None),
    ('question mark','Sam: When can we deploy?','question',None),
    ('ordinary status','Alex: The API tests passed.','none',None),
    ('historical work','Sam: I wrote the tests yesterday.','none',None),
    ('unknown speaker','Pat: I will run the migration by tomorrow.','action',None),
    ('missing deadline','Sam: I will check the logs.','action','Sam'),
    ('unnamed owner','Alex: ACTION: review the dashboard.','action',None),
    ('explicit negative decision','Alex: Decision: do not remove the audit logs.','decision',None),
    ('implicit commitment','Sam: Leave the load test with me.','action','Sam'),
    ('conditional noncommitment','Alex: I will deploy if legal approves.','none',None),
    ('negated intent','Alex: I will not own the release.','none',None),
    ('rhetorical question','Sam: Who would delete the audit log?','none',None),
    ('implicit decision','Alex: The queue it is, then.','decision',None),
    ('indirect assignment','Alex: Sam, please document the migration.','action','Sam'),
    ('ambiguous time','Sam: I will test soon.','action','Sam'),
    ('todo heading','Alex: Todo: Sam to review the retry policy by 2026-10-12.','action','Sam'),
    ('discussion context','Sam: We could consider a queue later.','none',None),
    ('question heading','Alex: Open question: Is the retention period sufficient?','question',None),
    ('decision paraphrase','Sam: The decision is to retain data for 30 days.','decision',None),
]


def evaluate() -> dict:
    rows=[];tp=fp=fn=owner_matches=owner_total=0
    for label,text,gold,owner in CASES:
        m=prepare_meeting({'title':'Fixture diagnostic','meeting_date':'2026-10-09',
                           'participants':['Alex','Sam'],'transcript':text})
        proposals=extract(m)['proposals'];predicted=proposals[0]['kind'] if proposals else 'none'
        correct=gold==predicted
        if gold!='none' and correct:tp+=1
        elif not correct:
            if predicted!='none':fp+=1
            if gold!='none':fn+=1
        if gold=='action' and predicted=='action':
            owner_total+=1;owner_matches+=proposals[0]['owner']==owner
        rows.append({'case':label,'transcript':text,'expected':gold,'predicted':predicted,'correct':correct,
                     'expected_owner':owner,'predicted_owner':proposals[0]['owner'] if proposals else None,
                     'flags':proposals[0]['flags'] if proposals else []})
    precision=tp/(tp+fp) if tp+fp else 0;recall=tp/(tp+fn) if tp+fn else 0
    return {'rule_version':RULE_VERSION,'dataset':'English fixture diagnostic v1','cases':len(rows),
            'true_positive':tp,'false_positive':fp,'false_negative':fn,
            'precision':round(precision,4),'recall':round(recall,4),
            'f1':round(2*precision*recall/(precision+recall),4) if precision+recall else 0,
            'owner_matches':owner_matches,'owner_evaluated':owner_total,'rows':rows,
            'limitations':['24 manually labeled English snippets; not a representative production benchmark.',
                           'Labels score the first candidate per turn, not semantic correctness or complete meeting coverage.',
                           'Implicit commitments, conditional statements and rhetorical questions need human review.',
                           'Owner agreement is measured only on correctly detected actions; it is not end-to-end owner recall.']}


if __name__=='__main__':
    import json
    print(json.dumps(evaluate(),indent=2))
