"""Portable exports; generated text is never sent to Slack or a calendar service."""
from __future__ import annotations
import csv
import io
import json
from datetime import date, timedelta
from app.core.errors import AppError


def safe_cell(value: object) -> str:
    text=str(value or '')
    # Spreadsheet formula evaluation can ignore leading whitespace.
    return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text


def markdown_escape(text: str) -> str:
    # Prevent transcript content becoming HTML, headings, links or table columns.
    for char in '\\`*_{}[]<>()#+-.!|':text=text.replace(char,'\\'+char)
    return text.replace('\n',' / ').replace('\r',' ')


def markdown(meeting: dict) -> str:
    lines=['# '+markdown_escape(meeting['title']),
           f"Date: {meeting['meeting_date']} · Revision: {meeting['revision']} · Status: {meeting['status']}",
           '', 'Participants: '+', '.join(markdown_escape(p) for p in meeting['participants']),
           '', 'Source SHA-256: `'+meeting['document']['sha256']+'`','']
    for kind,heading in [('decision','Decisions'),('action','Actions'),('question','Open questions')]:
        lines+=['## '+heading,'']
        items=[i for i in meeting['items'] if i['kind']==kind]
        if not items:lines+=['None recorded.','']
        for item in items:
            lines.append('- '+markdown_escape(item['text']))
            lines.append('  Status: '+item['status']+(f" · Owner: {markdown_escape(item.get('owner') or 'Unassigned')} · Due: {item.get('due_date') or 'Unconfirmed'}" if kind=='action' else ''))
            for ref in item['evidence']:
                lines.append(f"  Source {ref['turn_id']} (line {ref['line']}): “{markdown_escape(ref['quote'])}”")
            if item.get('note'):lines.append('  Review note: '+markdown_escape(item['note']))
            lines.append('')
    lines+=['Exports are a snapshot. Review source citations before sharing confidential meeting content.','']
    return '\n'.join(lines)


def slack(meeting: dict) -> str:
    def escape(value: str) -> str:
        # Escaping angle brackets also disables accidental @channel/user links.
        return value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    lines=[escape(meeting['title']),f"{meeting['meeting_date']} · {meeting['status']} · revision {meeting['revision']}"]
    for item in meeting['items'][:30]:
        suffix=f" — {item.get('owner') or 'Unassigned'}, due {item.get('due_date') or 'unconfirmed'}" if item['kind']=='action' else ''
        lines.append(f"• [{item['kind']}/{item['status']}] "+escape(item['text'].replace('\n',' ')[:500]+suffix))
    if len(meeting['items'])>30:lines.append(f"… {len(meeting['items'])-30} more items in the full minutes.")
    return '\n'.join(lines)+'\n'


def actions_csv(meeting: dict) -> str:
    out=io.StringIO(newline='');writer=csv.writer(out)
    writer.writerow(['meeting_id','action_id','task','owner','due_date','status','source_turns'])
    for item in meeting['items']:
        if item['kind']=='action':
            writer.writerow([safe_cell(v) for v in [meeting['id'],item['id'],item['text'],item.get('owner'),item.get('due_date'),item['status'],','.join(r['turn_id'] for r in item['evidence'])]])
    return out.getvalue()


def ics_escape(value: str) -> str:
    return value.replace('\\','\\\\').replace('\r','').replace('\n','\\n').replace(';','\\;').replace(',','\\,')


def fold_ics(line: str) -> str:
    """RFC 5545 folding counts UTF-8 bytes, never splits a Unicode character."""
    lines=[];current='';length=0
    for char in line:
        size=len(char.encode('utf-8'))
        if length+size>75:
            lines.append(current);current=' ';length=1
        current+=char;length+=size
    lines.append(current)
    return '\r\n'.join(lines)


def calendar(meeting: dict) -> str:
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Alan Vo//Meeting Minutes//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH']
    for item in meeting['items']:
        if item['kind']!='action' or not item.get('due_date') or item['status'] in {'done','cancelled'}:continue
        due=date.fromisoformat(item['due_date'])
        if due==date.max:raise AppError(422,'calendar_date','Calendar deadlines must be before 9999-12-31')
        description=f"Meeting: {meeting['title']}\nOwner: {item.get('owner') or 'Unassigned'}\nStatus: {item['status']}\n"+'\n'.join(f"{r['turn_id']}: {r['quote']}" for r in item['evidence'])
        lines+=['BEGIN:VEVENT',f"UID:{meeting['id']}-{item['id']}@meeting-minutes.local",
                'DTSTAMP:'+meeting['created_at'][:19].replace('-','').replace(':','')+'Z',
                'DTSTART;VALUE=DATE:'+due.isoformat().replace('-',''),
                'DTEND;VALUE=DATE:'+(due+timedelta(days=1)).isoformat().replace('-',''),
                'SUMMARY:'+ics_escape(item['text']),'DESCRIPTION:'+ics_escape(description),
                'TRANSP:TRANSPARENT','END:VEVENT']
    return '\r\n'.join(fold_ics(line) for line in lines+['END:VCALENDAR'])+'\r\n'


def export(meeting: dict, format: str) -> tuple[str,str,str]:
    if format=='json':return json.dumps(meeting,ensure_ascii=False,indent=2),'application/json','json'
    if format=='markdown':return markdown(meeting),'text/markdown','md'
    if format=='slack':return slack(meeting),'text/plain','txt'
    if format=='csv':return actions_csv(meeting),'text/csv','csv'
    if format=='ics':return calendar(meeting),'text/calendar','ics'
    raise AppError(422,'export_format','Supported formats: json, markdown, slack, csv, ics')
