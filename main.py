#!/usr/bin/env python3
"""Offline-compatible CLI sharing the web application's extraction/export engine."""
from __future__ import annotations
import argparse
from datetime import date,datetime,timezone
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'backend'))
from app.core.errors import AppError
from app.domain.transcript import prepare_meeting,PREFIX,RESERVED,MAX_TRANSCRIPT
from app.domain.extraction import extract
from app.domain.items import proposal_item
from app.domain.exports import markdown,slack


def run(argv=None):
    parser=argparse.ArgumentParser(description='Source-backed meeting minutes; no API key required')
    subs=parser.add_subparsers(dest='command',required=True)
    for name in ['minutes','actions','slack','followups']:
        p=subs.add_parser(name);source=p.add_mutually_exclusive_group(required=True)
        source.add_argument('--file');source.add_argument('--stdin',action='store_true')
        p.add_argument('--output');p.add_argument('--participants',help='Comma-separated exact names; otherwise use explicit speaker labels')
        p.add_argument('--meeting-date','--start-date',dest='meeting_date',default=date.today().isoformat(),help='YYYY-MM-DD deadline anchor; defaults to today')
        p.add_argument('--title',default='Meeting minutes')
        p.add_argument('--assign',action='store_true',help='Compatibility option; explicit owners are always extracted')
        p.add_argument('--channel',help='Compatibility option; output is never posted to Slack')
    args=parser.parse_args(argv)
    try:
        if args.stdin:text=sys.stdin.read(MAX_TRANSCRIPT+1)
        else:
            with open(args.file,encoding='utf-8') as f:text=f.read(MAX_TRANSCRIPT+1)
        names=[n.strip() for n in args.participants.split(',')] if args.participants else []
        if not names:
            for line in text.splitlines():
                match=PREFIX.match(line)
                if match and match['speaker'].strip().casefold() not in RESERVED:
                    name=match['speaker'].strip()
                    if name not in names:names.append(name)
        m=prepare_meeting({'title':args.title,'meeting_date':args.meeting_date,'participants':names or ['Unattributed'],'transcript':text})
        result=extract(m);m.update(id=m['document']['sha256'][:16],revision=1,status='draft',created_at=datetime.now(timezone.utc).isoformat(),items=[])
        for n,p in enumerate(result['proposals']):
            item=proposal_item(p,m);item.update(id=f'item-{n+1}');m['items'].append(item)
        if args.command=='minutes':output=markdown(m)
        elif args.command=='slack':output=slack(m)
        elif args.command=='actions':output=json.dumps([i for i in m['items'] if i['kind']=='action'],indent=2,ensure_ascii=False)+'\n'
        else:
            output=json.dumps([{'title':i['text'],'owner':i['owner'],'suggested_date':i['due_date'],'source':i['evidence']} for i in m['items'] if i['kind']=='action' and i['due_date']],indent=2,ensure_ascii=False)+'\n'
        if args.output:Path(args.output).write_text(output,encoding='utf-8')
        else:sys.stdout.write(output)
        return 0
    except (OSError,UnicodeError,AppError) as error:
        parser.exit(2,str(error)+'\n')


if __name__=='__main__':raise SystemExit(run())
