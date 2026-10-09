from datetime import date
import csv
import io
import pytest
from app.core.errors import AppError
from app.domain.transcript import prepare_meeting, citation
from app.domain.extraction import extract
from app.domain.deadlines import resolve_due
from app.domain.items import normalize_item
from app.domain.exports import export, fold_ics, safe_cell


def payload(**updates):
    return {'title':'API planning','meeting_date':'2026-10-09','participants':['Alex','Sam'],
            'kind':'planning','transcript':'[00:01] Alex: I will write the tests by tomorrow.\nSam: Decision: keep the REST API.\nAlex: Question: Who reviews the release?',**updates}


def test_offsets_cite_exact_normalized_source():
    m=prepare_meeting(payload(transcript='\r\n[00:01] Alex:   I will test by tomorrow.\r\nSam: café 🚀\r\n'))
    for t in m['document']['turns']:
        assert m['document']['text'][t['start']:t['end']]==t['text']
        ref=citation(m['document'],t['id'],t['text'])
        assert m['document']['text'][ref['start']:ref['end']]==ref['quote']
    assert m['document']['turns'][0]['speaker']=='Alex'


def test_extraction_has_citations_and_conservative_dates():
    m=prepare_meeting(payload());result=extract(m)['proposals']
    assert [p['kind'] for p in result]==['action','decision','question']
    assert result[0]['owner']=='Alex';assert result[0]['due']['date']=='2026-10-10'
    assert all(m['document']['text'][p['evidence'][0]['start']:p['evidence'][0]['end']]==p['evidence'][0]['quote'] for p in result)


def test_explicit_owner_longest_name_and_unknown_speaker():
    m=prepare_meeting(payload(participants=['Alex','Alex Kim'],transcript='Chris: ACTION: Alex Kim will deploy by Friday.\nChris: I will audit by soon.'))
    p=extract(m)['proposals'];assert p[0]['owner']=='Alex Kim';assert p[1]['owner'] is None
    assert 'owner_unresolved' in p[1]['flags'];assert m['document']['unknown_speakers']==['Chris']


def test_reserved_heading_is_not_a_speaker():
    m=prepare_meeting(payload(transcript='ACTION: Alex will run tests by Friday.'))
    assert m['document']['turns'][0]['raw_speaker'] is None
    assert extract(m)['proposals'][0]['kind']=='action'


def test_conditional_commitment_requires_review():
    p=extract(prepare_meeting(payload(transcript='Alex: I will deploy if tests pass by Friday.')))['proposals'][0]
    assert 'conditional_or_negative' in p['flags']
    assert p['due']['date']=='2026-10-09'


def test_no_invented_commitments():
    assert extract(prepare_meeting(payload(transcript='Alex: The build is currently green.')))['proposals']==[]


def test_duplicate_commitment_preserves_one_proposal():
    p=extract(prepare_meeting(payload(transcript='Alex: I will test by Friday.\nAlex: I will test by Friday.')))['proposals']
    assert len(p)==1


@pytest.mark.parametrize('field,value',[('title',''),('title',[]),('participants',[]),('participants',['Alex','alex']),('participants',['Alex:Boss']),('participants',[42]),('transcript',''),('transcript','a'*4001),('transcript','\ud800'),('transcript','hello\x00world'),('meeting_date','2026-02-30'),('meeting_date','10/09/26'),('kind',[]),('kind','unknown')])
def test_invalid_meeting_input(field,value):
    with pytest.raises(AppError) as e:prepare_meeting(payload(**{field:value}))
    assert e.value.status==422


@pytest.mark.parametrize('phrase,expected',[('tomorrow','2026-10-10'),('today','2026-10-09'),('Friday','2026-10-09'),('next Friday','2026-10-16'),('Monday','2026-10-12'),('in 3 days','2026-10-12'),('2026-10-20','2026-10-20'),('soon',None),('10/11',None),('2026-02-30',None),('in 999 days',None),('',None)])
def test_deadlines(phrase,expected):assert resolve_due(phrase,'2026-10-09')['date']==expected


def test_deadline_date_limit_does_not_crash():
    assert resolve_due('tomorrow','9999-12-31')['date'] is None
    assert resolve_due('2026-01-01','2026-10-09')['warning']=='Deadline precedes the meeting date'


def test_citation_cannot_invent_or_cross_turns():
    m=prepare_meeting(payload())
    for turn,quote in [('missing','text'),('t0001','I will hack everything'),('t0001','tomorrow.\nSam:')]:
        with pytest.raises(AppError):citation(m['document'],turn,quote)


def item_payload(m,**updates):
    return {'kind':'action','text':'Write tests','owner':'Alex','due_date':'2026-10-10',
            'evidence':[{'turn_id':'t0001','quote':m['document']['turns'][0]['text']}],**updates}


@pytest.mark.parametrize('updates',[{'kind':[]},{'status':[]},{'owner':'Unknown'},{'due_date':'2026-02-30'},{'evidence':[]},{'evidence':[None]},{'kind':'decision','owner':'Alex'},{'text':''}])
def test_invalid_item(updates):
    m=prepare_meeting(payload())
    with pytest.raises(AppError):normalize_item(item_payload(m,**updates),m)


@pytest.mark.parametrize('value',['=1+1',' +2','\t@SUM(A1)','-2+3'])
def test_formula_safety(value):assert safe_cell(value).startswith("'")


def test_calendar_folding_counts_utf8_bytes():
    line='SUMMARY:'+('界🚀'*50)
    folded=fold_ics(line)
    assert all(len(s.encode())<=75 for s in folded.split('\r\n'))
    assert folded.replace('\r\n ','')==line


def exported_meeting():
    m=prepare_meeting(payload());i=normalize_item(item_payload(m),m)
    i.update(id='item-one');m.update(id='meeting-one',revision=4,status='approved',created_at='2026-10-09T12:00:00+00:00',items=[i])
    return m


def test_exports_keep_evidence_and_escape_untrusted_content():
    m=exported_meeting();m['items'][0]['text']='=HYPERLINK("https://example.invalid")\nBEGIN:VEVENT'
    csv_text=export(m,'csv')[0];rows=list(csv.reader(io.StringIO(csv_text)))
    assert rows[1][2].startswith("'=")
    calendar=export(m,'ics')[0]
    assert calendar.count('\r\nBEGIN:VEVENT\r\n')==1
    assert 'DTSTART;VALUE=DATE:20261010' in calendar
    assert 'DTEND;VALUE=DATE:20261011' in calendar
    assert '\\nBEGIN:VEVENT' in calendar
    assert 'Source t0001' in export(m,'markdown')[0]
    m['items'][0]['text']='<!channel> <script>'
    assert '<!channel>' not in export(m,'slack')[0]
    assert '<script>' not in export(m,'markdown')[0]


def test_calendar_omits_completed_and_undated_actions():
    m=exported_meeting();m['items'][0]['status']='done'
    assert 'BEGIN:VEVENT' not in export(m,'ics')[0]
    m['items'][0]['status']='open';m['items'][0]['due_date']=None
    assert 'BEGIN:VEVENT' not in export(m,'ics')[0]


def test_calendar_rejects_max_date_and_unknown_format():
    m=exported_meeting();m['items'][0]['due_date']='9999-12-31'
    with pytest.raises(AppError):export(m,'ics')
    with pytest.raises(AppError):export(m,'pdf')


def test_cli_preserves_offline_commands(tmp_path):
    import subprocess,sys,json
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    source=tmp_path/'transcript.txt';source.write_text(payload()['transcript'])
    for command in ['minutes','actions','slack','followups']:
        r=subprocess.run([sys.executable,str(root/'main.py'),command,'--file',str(source),'--meeting-date','2026-10-09'],capture_output=True,text=True)
        assert r.returncode==0,r.stderr
        if command=='minutes':assert 'Source t0001' in r.stdout
        elif command=='actions':assert json.loads(r.stdout)[0]['owner']=='Alex'
        elif command=='followups':assert json.loads(r.stdout)[0]['suggested_date']=='2026-10-10'
        else:assert 'write the tests' in r.stdout
