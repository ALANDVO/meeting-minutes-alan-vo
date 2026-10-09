"""Authenticated meeting minutes API. All state changes use optimistic revisions."""
from contextlib import asynccontextmanager
import json
from typing import Literal
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from app.core.config import Settings, load_settings, validate_settings, ensure_db_dir
from app.core.db import Database
from app.core.auth import router as auth_router, authorize, OIDCClient
from app.core.errors import AppError
from app.services.meetings import MeetingService
from app.services.advice import AdviceService
from app.services.evaluation import evaluate
from app.domain.exports import export
from app.domain.items import review_findings
from app.domain.extraction import meeting_digest


class BodyLimit:
    def __init__(self,app,limit):self.app=app;self.limit=limit
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        messages=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            size+=len(message.get('body',b''))
            if size>self.limit:
                return await JSONResponse({'error':{'code':'request_too_large','message':'Request exceeds the configured body limit'}},status_code=413)(scope,receive,send)
            messages.append(message)
            if not message.get('more_body',False):break
        async def replay():
            if messages:return messages.pop(0)
            return await receive()
        await self.app(scope,replay,send)


class StrictBody(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class MeetingBody(StrictBody):
    title:str=Field(min_length=1,max_length=160)
    meeting_date:str
    participants:list[str]=Field(min_length=1,max_length=50)
    transcript:str=Field(min_length=1,max_length=100000)
    kind:Literal['standup','design_review','one_on_one','planning','retrospective','general']='general'
class Revision(StrictBody):revision:StrictInt=Field(ge=1)
class Adopt(Revision):proposal_ids:list[str]=Field(min_length=1,max_length=200)
class ItemBody(Revision):item:dict
class Review(Revision):
    decision:Literal['approve','request_changes']
    note:str=Field(min_length=1,max_length=2000)
class Reason(Revision):reason:str=Field(min_length=1,max_length=1000)
class Transition(Reason):status:Literal['open','in_progress','blocked','done','cancelled']
class AdviceRequest(Revision):consent:Literal[True]


def create_app(settings:Settings|None=None,oidc_transport=None,llm_transport=None):
    settings=settings or load_settings()
    @asynccontextmanager
    async def lifespan(app):
        validate_settings(settings);ensure_db_dir(settings.database_path)
        db=Database(settings.database_path);app.state.db=db;app.state.meetings=MeetingService(db)
        try:yield
        finally:db.close()
    app=FastAPI(title='Meeting Minutes — Alan Vo',version='1.0.0',lifespan=lifespan)
    app.state.settings=settings;app.state.oidc=OIDCClient(settings,oidc_transport)
    app.state.advice=AdviceService(settings,llm_transport)
    app.add_middleware(BodyLimit,limit=settings.max_upload_bytes)
    app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_url],allow_credentials=True,
                       allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Content-Type','X-CSRF-Token'])
    app.include_router(auth_router)
    @app.exception_handler(AppError)
    async def app_error(request,exc):return JSONResponse({'error':{'code':exc.code,'message':exc.message}},status_code=exc.status)
    @app.middleware('http')
    async def response_headers(request,call_next):
        response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store';response.headers['Referrer-Policy']='same-origin'
        return response
    def svc(request):return request.app.state.meetings
    def actor(request,role='reviewer'):return authorize(request,role)['subject']

    @app.get('/api/health')
    def health():return {'status':'ok','version':'1.0.0'}
    @app.get('/api/evaluation')
    def evaluation(request:Request):actor(request,'viewer');return evaluate()
    @app.get('/api/meetings')
    def meetings(request:Request,q:str=Query('',max_length=160),status:str=Query('',max_length=20)):
        actor(request,'viewer');return svc(request).list(q,status)
    @app.post('/api/meetings/preview')
    def preview(body:MeetingBody,request:Request):
        actor(request);return svc(request).preview(body.model_dump())
    @app.post('/api/meetings',status_code=201)
    def create(body:MeetingBody,request:Request):return svc(request).create(body.model_dump(),actor(request))
    @app.get('/api/meetings/{meeting_id}')
    def get(meeting_id:str,request:Request):
        actor(request,'viewer');m=svc(request).get(meeting_id)
        return {**m,'digest':meeting_digest(m,m['items']),'review_findings':review_findings(m)}
    @app.post('/api/meetings/{meeting_id}/adopt')
    def adopt(meeting_id:str,body:Adopt,request:Request):return svc(request).adopt(meeting_id,body.revision,body.proposal_ids,actor(request))
    @app.post('/api/meetings/{meeting_id}/items')
    def add_item(meeting_id:str,body:ItemBody,request:Request):return svc(request).add_item(meeting_id,body.revision,body.item,actor(request))
    @app.put('/api/meetings/{meeting_id}/items/{item_id}')
    def edit_item(meeting_id:str,item_id:str,body:ItemBody,request:Request):return svc(request).edit_item(meeting_id,body.revision,item_id,body.item,actor(request))
    @app.delete('/api/meetings/{meeting_id}/items/{item_id}')
    def remove_item(meeting_id:str,item_id:str,body:Revision,request:Request):return svc(request).remove_item(meeting_id,body.revision,item_id,actor(request))
    @app.post('/api/meetings/{meeting_id}/submit')
    def submit(meeting_id:str,body:Revision,request:Request):return svc(request).submit(meeting_id,body.revision,actor(request))
    @app.post('/api/meetings/{meeting_id}/review')
    def review(meeting_id:str,body:Review,request:Request):return svc(request).review(meeting_id,body.revision,body.decision,body.note,actor(request))
    @app.post('/api/meetings/{meeting_id}/reopen')
    def reopen(meeting_id:str,body:Reason,request:Request):return svc(request).reopen(meeting_id,body.revision,body.reason,actor(request))
    @app.post('/api/meetings/{meeting_id}/items/{item_id}/transition')
    def transition(meeting_id:str,item_id:str,body:Transition,request:Request):return svc(request).transition(meeting_id,body.revision,item_id,body.status,body.reason,actor(request))
    @app.get('/api/meetings/{meeting_id}/releases')
    def releases(meeting_id:str,request:Request):actor(request,'viewer');return svc(request).releases(meeting_id)
    @app.get('/api/meetings/{meeting_id}/export/{format}')
    def download(meeting_id:str,format:str,request:Request,release:int|None=Query(None,ge=1)):
        actor(request,'viewer');m=svc(request).release(meeting_id,release) if release is not None else svc(request).get(meeting_id)
        text,mime,suffix=export(m,format)
        return Response(text,media_type=mime,headers={'Content-Disposition':f'attachment; filename="minutes-{m["id"]}-r{m["revision"]}.{suffix}"'})
    @app.get('/api/audit')
    def audit(request:Request,meeting_id:str|None=None):actor(request,'viewer');return svc(request).audit(meeting_id)
    @app.delete('/api/meetings/{meeting_id}',status_code=204)
    def delete(meeting_id:str,body:Revision,request:Request):svc(request).delete(meeting_id,body.revision,actor(request,'admin'));return Response(status_code=204)
    @app.post('/api/meetings/{meeting_id}/suggestions')
    def suggestions(meeting_id:str,body:AdviceRequest,request:Request):
        actor(request);m=svc(request).get(meeting_id)
        if m['revision']!=body.revision:raise AppError(409,'revision_conflict','Reload before requesting suggestions')
        return app.state.advice.suggest(m)
    return app


app=create_app()
