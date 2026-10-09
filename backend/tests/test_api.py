import httpx
import json
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings, ConfigError
from app.core.auth import create_session
from app.main import create_app
from fastapi import Response
from test_domain import payload


@pytest.fixture
def client(tmp_path):
    app=create_app(Settings(environment='test',auth_mode='demo',cookie_secure=False,database_path=str(tmp_path/'minutes.db')))
    with TestClient(app) as client:yield client


def login(client,identity='analyst'):
    r=client.post('/api/auth/demo',params={'identity':identity});assert r.status_code==200,r.text
    return {'X-CSRF-Token':r.json()['csrf_token']}


def test_api_review_and_export_workflow(client):
    assert client.get('/api/meetings').status_code==401
    headers=login(client);r=client.post('/api/meetings',json=payload(),headers=headers);assert r.status_code==201
    m=r.json();url='/api/meetings/'+m['id']
    m=client.post(url+'/adopt',json={'revision':m['revision'],'proposal_ids':['p0001','p0002','p0003']},headers=headers).json()
    m=client.post(url+'/submit',json={'revision':m['revision']},headers=headers).json()
    assert client.post(url+'/review',json={'revision':m['revision'],'decision':'approve','note':'checked'},headers=headers).status_code==403
    headers=login(client,'reviewer')
    r=client.post(url+'/review',json={'revision':m['revision'],'decision':'approve','note':'Compared against source'},headers=headers)
    assert r.status_code==200,r.text;m=r.json()
    assert m['status']=='approved'
    for kind in ['json','markdown','csv','slack','ics']:
        r=client.get(url+'/export/'+kind);assert r.status_code==200
        assert 'attachment' in r.headers['content-disposition'];assert r.headers['cache-control']=='no-store'
    assert client.get(url+'/releases').json()[0]['revision']==m['revision']
    assert client.get('/api/audit',params={'meeting_id':m['id']}).json()[0]['action']=='minutes.approved'


def test_csrf_and_unknown_revision_are_rejected(client):
    headers=login(client)
    assert client.post('/api/meetings',json=payload()).status_code==403
    m=client.post('/api/meetings',json=payload(),headers=headers).json()
    for bad in [True,'1',0]:
        assert client.post('/api/meetings/'+m['id']+'/submit',json={'revision':bad},headers=headers).status_code==422


def test_viewer_cannot_mutate(client):
    response=Response();user=create_session(client.app.state.db,client.app.state.settings,response,'reader','Reader',['viewer'])
    cookie=response.headers['set-cookie'].split(';')[0].split('=',1)
    client.cookies.set(*cookie)
    assert client.get('/api/meetings').status_code==200
    assert client.post('/api/meetings',json=payload(),headers={'X-CSRF-Token':user['csrf_token']}).status_code==403


def test_demo_refuses_cross_origin_and_production(tmp_path,client):
    assert client.post('/api/auth/demo',headers={'Origin':'https://untrusted.example'}).status_code==403
    with pytest.raises(ConfigError):
        with TestClient(create_app(Settings(environment='production',auth_mode='demo',database_path=str(tmp_path/'bad.db')))):pass


def test_request_size_is_enforced_before_processing(tmp_path):
    with TestClient(create_app(Settings(environment='test',auth_mode='demo',cookie_secure=False,database_path=str(tmp_path/'tiny.db'),max_upload_bytes=100))) as c:
        h=login(c)
        assert c.post('/api/meetings',json=payload(),headers=h).status_code==413


def test_missing_advice_key_does_not_damage_meeting(client):
    h=login(client);m=client.post('/api/meetings',json=payload(),headers=h).json();url='/api/meetings/'+m['id']
    assert client.post(url+'/suggestions',json={'revision':1,'consent':False},headers=h).status_code==422
    assert client.post(url+'/suggestions',json={'revision':1,'consent':True},headers=h).status_code==503
    assert client.get(url).json()['revision']==1


def test_logout_invalidates_server_side_session(client):
    h=login(client);assert client.get('/api/auth/me').status_code==200
    assert client.post('/api/auth/logout',headers=h).status_code==204
    assert client.get('/api/auth/me').status_code==401


def test_malformed_unicode_state_is_unauthorized_not_server_error(client):
    assert client.get('/api/auth/callback',params={'state':'é','code':'unused'}).status_code==401


def test_malformed_csrf_header_is_forbidden_not_server_error(client):
    login(client)
    assert client.post('/api/meetings',json=payload(),headers=[(b'X-CSRF-Token',b'\xff')]).status_code==403
