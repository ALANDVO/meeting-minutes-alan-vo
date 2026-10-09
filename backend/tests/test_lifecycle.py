import concurrent.futures
import pytest
from app.core.db import Database
from app.core.errors import AppError
from app.services.meetings import MeetingService
from test_domain import payload, item_payload


@pytest.fixture
def service():
    db=Database(':memory:');service=MeetingService(db)
    yield service
    db.close()


def adopted(service):
    m=service.create(payload(),'author')
    return service.adopt(m['id'],m['revision'],[p['id'] for p in m['proposals']],'author')


def approved(service):
    m=adopted(service);m=service.submit(m['id'],m['revision'],'author')
    return service.review(m['id'],m['revision'],'approve','Source checked; dates confirmed','reviewer')


def test_full_lifecycle_and_immutable_approved_snapshot(service):
    m=approved(service);release_revision=m['revision'];item=m['items'][0]
    m=service.transition(m['id'],m['revision'],item['id'],'done','Tests passed','author')
    assert m['items'][0]['status']=='done'
    assert service.release(m['id'],release_revision)['items'][0]['status']=='open'
    assert service.releases(m['id'])[0]['revision']==release_revision
    assert service.audit(m['id'])[0]['action']=='action.transitioned'


def test_self_approval_is_forbidden(service):
    m=adopted(service);m=service.submit(m['id'],m['revision'],'author')
    with pytest.raises(AppError) as e:service.review(m['id'],m['revision'],'approve','Checked','author')
    assert e.value.status==403;assert service.get(m['id'])['status']=='submitted'


def test_past_editor_cannot_approve_after_item_removal(service):
    m=adopted(service);m=service.add_item(m['id'],m['revision'],item_payload(m),'editor')
    m=service.remove_item(m['id'],m['revision'],m['items'][-1]['id'],'author')
    m=service.submit(m['id'],m['revision'],'author')
    with pytest.raises(AppError):service.review(m['id'],m['revision'],'approve','Checked','editor')


def test_reopen_keeps_approval_history_and_allows_changes(service):
    m=approved(service);r=m['revision'];m=service.reopen(m['id'],r,'Correct owner','author')
    assert m['status']=='draft';assert service.release(m['id'],r)['status']=='approved'
    m=service.edit_item(m['id'],m['revision'],m['items'][0]['id'],{**m['items'][0],'owner':'Sam'},'author')
    assert m['items'][0]['owner']=='Sam'


def test_conflicting_updates_are_atomic(service):
    m=adopted(service);rev=m['revision'];id=m['id']
    def change(actor):
        try:return service.add_item(id,rev,item_payload(m),actor)['revision']
        except AppError as e:return e.code
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(change,['one','two']))
    assert sorted(map(str,results))==sorted([str(rev+1),'revision_conflict'])
    assert len(service.get(id)['items'])==4


def test_bad_adoption_rolls_back_without_partial_items(service):
    m=service.create(payload(),'author')
    with pytest.raises(AppError):service.adopt(m['id'],1,['p0001','missing'],'author')
    assert service.get(m['id'])['revision']==1;assert service.get(m['id'])['items']==[]
    assert len(service.audit(m['id']))==1


def test_duplicate_adoption_is_rejected(service):
    m=adopted(service)
    with pytest.raises(AppError):service.adopt(m['id'],m['revision'],['p0001'],'author')


def test_empty_minutes_cannot_be_submitted(service):
    m=service.create(payload(),'author')
    with pytest.raises(AppError):service.submit(m['id'],1,'author')


def test_review_rejection_restores_draft(service):
    m=adopted(service);m=service.submit(m['id'],m['revision'],'author')
    m=service.review(m['id'],m['revision'],'request_changes','Confirm ambiguous deadline','reviewer')
    assert m['status']=='draft';assert not service.releases(m['id'])


def test_editing_submitted_or_approved_minutes_is_rejected(service):
    m=approved(service)
    with pytest.raises(AppError):service.remove_item(m['id'],m['revision'],m['items'][0]['id'],'author')


def test_transition_requires_owner_and_reason(service):
    m=adopted(service)
    m=service.edit_item(m['id'],m['revision'],m['items'][0]['id'],{**m['items'][0],'owner':None},'author')
    m=service.submit(m['id'],m['revision'],'author');m=service.review(m['id'],m['revision'],'approve','Unassigned action acknowledged','reviewer')
    with pytest.raises(AppError):service.transition(m['id'],m['revision'],m['items'][0]['id'],'done','Finished','author')
    with pytest.raises(AppError):service.transition(m['id'],m['revision'],m['items'][0]['id'],'in_progress','','author')


def test_delete_checks_revision_and_retains_audit(service):
    m=approved(service)
    with pytest.raises(AppError):service.delete(m['id'],1,'admin')
    service.delete(m['id'],m['revision'],'admin')
    with pytest.raises(AppError):service.get(m['id'])
    assert service.audit(m['id'])[0]['action']=='meeting.deleted'
    assert service.db.query('SELECT * FROM releases')==[]


def test_search_and_digest(service):
    m=adopted(service)
    assert service.list('API')[0]['digest']['counts']=={'action':1,'decision':1,'question':1}
    assert service.list('missing')==[]
    assert service.list(status='approved')==[]


@pytest.mark.parametrize('revision',[True,0,-1,'1',None])
def test_revision_is_strict(service,revision):
    m=service.create(payload(),'author')
    with pytest.raises(AppError):service.submit(m['id'],revision,'author')
