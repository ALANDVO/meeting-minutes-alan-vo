"""Transactional meeting lifecycle, immutable approved minutes and audit events."""
from __future__ import annotations
import json
import uuid
from app.core.db import Database, utcnow
from app.core.errors import AppError
from app.domain.transcript import prepare_meeting, clean_text, fail
from app.domain.extraction import extract, meeting_digest
from app.domain.items import normalize_item, proposal_item, validate_transition, review_findings

SCHEMA='''
CREATE TABLE IF NOT EXISTS meetings(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS releases(meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE, revision INTEGER NOT NULL, data TEXT NOT NULL, approved_by TEXT NOT NULL, approved_at TEXT NOT NULL, PRIMARY KEY(meeting_id, revision));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_id TEXT, actor TEXT NOT NULL, action TEXT NOT NULL, revision INTEGER, detail TEXT NOT NULL, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS audit_meeting ON audit(meeting_id,id);
'''


def identifier() -> str:return uuid.uuid4().hex


class MeetingService:
    def __init__(self,db:Database):
        self.db=db
        with db._lock:db._conn.executescript(SCHEMA)

    @staticmethod
    def _event(conn,meeting_id,actor,action,revision,detail):
        conn.execute('INSERT INTO audit(meeting_id,actor,action,revision,detail,at) VALUES (?,?,?,?,?,?)',
                     (meeting_id,actor,action,revision,json.dumps(detail),utcnow()))
        conn.execute('DELETE FROM audit WHERE id NOT IN (SELECT id FROM audit ORDER BY id DESC LIMIT 5000)')

    def preview(self,payload:dict) -> dict:
        meeting=prepare_meeting(payload)
        return {**meeting,**extract(meeting)}

    def create(self,payload:dict,actor:str) -> dict:
        data=self.preview(payload);stamp=utcnow()
        data.update(id=identifier(),revision=1,status='draft',items=[],created_by=actor,
                    created_at=stamp,updated_at=stamp,submitted_by=None,approval=None,review_note='',contributors=[actor])
        with self.db.transaction() as conn:
            if conn.execute('SELECT COUNT(*) FROM meetings').fetchone()[0]>=200:
                raise AppError(409,'capacity','Meeting limit reached (200); export old meetings, then delete them')
            conn.execute('INSERT INTO meetings VALUES (?,?,?,?)',(data['id'],1,json.dumps(data),stamp))
            self._event(conn,data['id'],actor,'meeting.created',1,{'source_sha256':data['document']['sha256']})
        return data

    def get(self,meeting_id:str) -> dict:
        row=self.db.query_one('SELECT data FROM meetings WHERE id=?',(meeting_id,))
        if not row:raise AppError(404,'meeting_not_found','Meeting does not exist')
        return json.loads(row['data'])

    def list(self,query:str='',status:str='') -> list[dict]:
        result=[]
        for row in self.db.query('SELECT data FROM meetings ORDER BY updated_at DESC,id LIMIT 200'):
            m=json.loads(row['data'])
            if status and m['status']!=status:continue
            if query and query.casefold() not in m['title'].casefold():continue
            result.append({k:m[k] for k in ['id','title','meeting_date','kind','revision','status','created_by','updated_at']}|
                          {'digest':meeting_digest(m,m['items'])})
        return result

    def mutate(self,meeting_id:str,revision:int,actor:str,action:str,callback) -> dict:
        if type(revision) is not int or revision<1:fail('revision must be a positive integer')
        with self.db.transaction() as conn:
            row=conn.execute('SELECT data FROM meetings WHERE id=?',(meeting_id,)).fetchone()
            if not row:raise AppError(404,'meeting_not_found','Meeting does not exist')
            data=json.loads(row['data'])
            if data['revision']!=revision:raise AppError(409,'revision_conflict','Meeting changed; reload before applying this change')
            detail=callback(data)
            if action.startswith(('item.','proposals.')) or action=='minutes.reopened':
                data['contributors']=sorted(set(data.get('contributors',[]))|{actor})
            data['revision']+=1;data['updated_at']=utcnow()
            conn.execute('UPDATE meetings SET revision=?,data=?,updated_at=? WHERE id=?',
                         (data['revision'],json.dumps(data),data['updated_at'],meeting_id))
            self._event(conn,meeting_id,actor,action,data['revision'],detail)
            if action=='minutes.approved':
                conn.execute('INSERT INTO releases VALUES (?,?,?,?,?)',(meeting_id,data['revision'],json.dumps(data),actor,data['updated_at']))
                conn.execute('DELETE FROM releases WHERE meeting_id=? AND revision NOT IN (SELECT revision FROM releases WHERE meeting_id=? ORDER BY revision DESC LIMIT 25)',(meeting_id,meeting_id))
            return data

    @staticmethod
    def _draft(data):
        if data['status']!='draft':raise AppError(409,'not_draft','Reopen minutes as a draft before editing their content')

    def add_item(self,meeting_id,revision,payload,actor):
        def apply(data):
            self._draft(data)
            if len(data['items'])>=200:raise AppError(409,'item_limit','Meeting item limit reached (200)')
            item=normalize_item(payload,data)
            item.update(id=identifier(),source='human',created_by=actor)
            data['items'].append(item)
            return {'item_id':item['id'],'kind':item['kind']}
        return self.mutate(meeting_id,revision,actor,'item.added',apply)

    def adopt(self,meeting_id,revision,proposal_ids,actor):
        if not isinstance(proposal_ids,list) or not proposal_ids or len(proposal_ids)>200 or any(not isinstance(i,str) for i in proposal_ids):fail('proposal_ids must be a nonempty list of IDs')
        if len(set(proposal_ids))!=len(proposal_ids):fail('Duplicate proposal IDs')
        def apply(data):
            self._draft(data)
            proposals={p['id']:p for p in data['proposals']}
            if any(i not in proposals for i in proposal_ids):fail('Unknown proposal ID')
            adopted={i.get('proposal_id') for i in data['items']}
            if any(i in adopted for i in proposal_ids):raise AppError(409,'already_adopted','One or more proposals were already adopted')
            if len(data['items'])+len(proposal_ids)>200:raise AppError(409,'item_limit','Meeting item limit reached (200)')
            for proposal_id in proposal_ids:
                item=proposal_item(proposals[proposal_id],data)
                item.update(id=identifier(),source='rules',proposal_id=proposal_id,created_by=actor)
                data['items'].append(item)
            return {'proposal_ids':proposal_ids}
        return self.mutate(meeting_id,revision,actor,'proposals.adopted',apply)

    def edit_item(self,meeting_id,revision,item_id,payload,actor):
        def apply(data):
            self._draft(data)
            index=next((n for n,i in enumerate(data['items']) if i['id']==item_id),None)
            if index is None:raise AppError(404,'item_not_found','Item does not exist')
            prior=data['items'][index]
            item=normalize_item(payload,data)
            if item['kind']!=prior['kind']:fail('Item kind cannot change; create a separate sourced item')
            data['items'][index]={**prior,**item,'source':'human-reviewed','edited_by':actor}
            return {'item_id':item_id}
        return self.mutate(meeting_id,revision,actor,'item.edited',apply)

    def remove_item(self,meeting_id,revision,item_id,actor):
        def apply(data):
            self._draft(data)
            if not any(i['id']==item_id for i in data['items']):raise AppError(404,'item_not_found','Item does not exist')
            data['items']=[i for i in data['items'] if i['id']!=item_id]
            return {'item_id':item_id}
        return self.mutate(meeting_id,revision,actor,'item.removed',apply)

    def submit(self,meeting_id,revision,actor):
        def apply(data):
            self._draft(data);findings=review_findings(data)
            if any(f['severity']=='blocking' for f in findings):raise AppError(409,'review_blocked','Minutes need at least one sourced item')
            data['status']='submitted';data['submitted_by']=actor;data['review_note']=''
            return {'warnings':len(findings)}
        return self.mutate(meeting_id,revision,actor,'minutes.submitted',apply)

    def review(self,meeting_id,revision,decision,note,actor):
        if decision not in ('approve','request_changes'):fail('decision must be approve or request_changes')
        note=clean_text(note,'review note',2000,multiline=True)
        def apply(data):
            if data['status']!='submitted':raise AppError(409,'not_submitted','Minutes are not awaiting review')
            editors=set(data.get('contributors',[]))|{data['created_by'],data['submitted_by']}|{i.get('created_by') for i in data['items']}|{i.get('edited_by') for i in data['items']}
            if actor in editors:raise AppError(403,'independent_review','A different participant must review these minutes')
            data['review_note']=note
            if decision=='approve':
                data['status']='approved';data['approval']={'actor':actor,'at':utcnow(),'revision':revision+1,'note':note}
            else:data['status']='draft'
            return {'decision':decision,'note':note}
        return self.mutate(meeting_id,revision,actor,'minutes.approved' if decision=='approve' else 'minutes.changes_requested',apply)

    def reopen(self,meeting_id,revision,reason,actor):
        reason=clean_text(reason,'reopen reason',1000,multiline=True)
        def apply(data):
            if data['status'] not in {'approved','submitted'}:raise AppError(409,'cannot_reopen','Only submitted or approved minutes may be reopened')
            data['status']='draft';data['submitted_by']=None
            return {'reason':reason}
        return self.mutate(meeting_id,revision,actor,'minutes.reopened',apply)

    def transition(self,meeting_id,revision,item_id,status,reason,actor):
        def apply(data):
            if data['status']!='approved':raise AppError(409,'not_approved','Approve minutes before updating execution status')
            item=next((i for i in data['items'] if i['id']==item_id),None)
            if item is None:raise AppError(404,'item_not_found','Item does not exist')
            note=validate_transition(item,status,reason);prior=item['status'];item['status']=status
            item['last_transition']={'actor':actor,'at':utcnow(),'reason':note}
            return {'item_id':item_id,'from':prior,'to':status,'reason':note}
        return self.mutate(meeting_id,revision,actor,'action.transitioned',apply)

    def releases(self,meeting_id):
        self.get(meeting_id)
        return [dict(r) for r in self.db.query('SELECT revision,approved_by,approved_at FROM releases WHERE meeting_id=? ORDER BY revision DESC',(meeting_id,))]

    def release(self,meeting_id,revision):
        row=self.db.query_one('SELECT data FROM releases WHERE meeting_id=? AND revision=?',(meeting_id,revision))
        if not row:raise AppError(404,'release_not_found','Approved snapshot does not exist')
        return json.loads(row['data'])

    def audit(self,meeting_id=None):
        rows=self.db.query('SELECT * FROM audit WHERE meeting_id=? ORDER BY id DESC LIMIT 200',(meeting_id,)) if meeting_id else self.db.query('SELECT * FROM audit ORDER BY id DESC LIMIT 200')
        return [{**dict(r),'detail':json.loads(r['detail'])} for r in rows]

    def delete(self,meeting_id,revision,actor):
        def apply(data):
            if data['status']=='submitted':raise AppError(409,'review_in_progress','Resolve or reopen the submitted review before deletion')
            return {}
        # Deletion and its revision check must occur in one transaction.
        if type(revision) is not int or revision<1:fail('revision must be a positive integer')
        with self.db.transaction() as conn:
            row=conn.execute('SELECT data FROM meetings WHERE id=?',(meeting_id,)).fetchone()
            if not row:raise AppError(404,'meeting_not_found','Meeting does not exist')
            data=json.loads(row['data'])
            if data['revision']!=revision:raise AppError(409,'revision_conflict','Meeting changed; reload before deleting')
            apply(data);conn.execute('DELETE FROM meetings WHERE id=?',(meeting_id,))
            self._event(conn,meeting_id,actor,'meeting.deleted',revision,{'title':data['title']})
