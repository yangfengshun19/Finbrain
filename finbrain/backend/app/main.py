import os
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .service import Service, ServiceError
from .store import Store

ROOT = Path(__file__).resolve().parents[2]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(StrictModel):
    user_id: str


class Snapshot(StrictModel):
    snapshot: str


class Question(StrictModel):
    question: str = Field(min_length=1, max_length=2000)


class Feedback(StrictModel):
    query_id: str
    resolved: bool


class Topic(StrictModel):
    topic_id: str


class Review(StrictModel):
    approve: bool


class ActionCheck(StrictModel):
    resource_id: str
    version: int = Field(ge=1)


def create_app(runtime=None):
    app = FastAPI(title='FinBrain local demo', version='0.1.0')
    store = Store(Path(runtime or ROOT / 'runtime'))
    service = Service(store)
    app.state.service = service

    @app.exception_handler(ServiceError)
    async def service_error(request, exc):
        return JSONResponse({'detail': exc.message}, status_code=exc.status)

    @app.middleware('http')
    async def local_boundary(request, call_next):
        host = request.headers.get('host', '').split(':')[0]
        if host not in ('127.0.0.1', 'localhost', 'testserver'):
            return JSONResponse({'detail': 'Only local demo access is allowed.'}, status_code=403)
        origin = request.headers.get('origin')
        if origin and urlparse(origin).netloc != request.headers.get('host'):
            return JSONResponse({'detail': 'Request origin does not match.'}, status_code=403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get('x-finbrain-client') != '1':
            return JSONResponse({'detail': 'Missing application request marker.'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        return response

    def actor(request):
        auth = request.headers.get('authorization', '')
        token = auth[7:] if auth.startswith('Bearer ') else request.cookies.get('finbrain_session', '')
        return service.authenticate(token)

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'demo': True, 'mode': os.getenv('FINBRAIN_ANSWER_MODE', 'extractive')}

    @app.get('/api/demo/config')
    def config():
        state = service.knowledge.state()
        return {'users': list(state['users'].values()), 'events': [{'snapshot': e['snapshot'], 'effective_at': e['effective_at'], 'title': e['title']} for e in service.knowledge.dataset['events']],
                'snapshot': state['snapshot'], 'label': 'Local demo console · Global timeline · Not production authentication'}

    @app.post('/api/demo/login')
    def login(body: Login, response: Response):
        token = service.login(body.user_id)
        response.set_cookie('finbrain_session', token, httponly=True, samesite='strict', max_age=28800)
        return {'ok': True}

    @app.post('/api/demo/snapshot')
    def snapshot(body: Snapshot):
        if body.snapshot not in service.knowledge.snapshots: raise ServiceError(400, 'Unknown timeline checkpoint.')
        with service.lock:
            store.set_setting('snapshot', body.snapshot)
        return {'snapshot': body.snapshot}

    @app.post('/api/demo/seed')
    def seed():
        return service.demo_seed()

    @app.post('/api/me/tool-token')
    def tool_token(request: Request):
        return {'token': service.login(actor(request)), 'expires_in_hours': 8}

    @app.get('/api/me')
    def me(request: Request): return service.me(actor(request))

    @app.get('/api/briefings')
    def briefings(request: Request): return service.briefings(actor(request))

    @app.post('/api/briefings/{rid}/read')
    def read(rid: str, request: Request): return service.mark_read(actor(request), rid)

    @app.post('/api/questions')
    def ask(body: Question, request: Request): return service.ask(actor(request), body.question)

    @app.post('/api/feedback')
    def feedback(body: Feedback, request: Request): return service.feedback(actor(request), body.query_id, body.resolved)

    @app.get('/api/resources/{rid}')
    def resource(rid: str, request: Request): return service.resource(actor(request), rid)

    @app.get('/api/timeline')
    def timeline(request: Request): return service.timeline(actor(request))

    @app.post('/api/action-check')
    def check(body: ActionCheck, request: Request): return service.action_check(actor(request), body.resource_id, body.version)

    @app.get('/api/hotspots')
    def hotspots(request: Request): return service.hotspots(actor(request))

    @app.post('/api/hotspots/publish')
    def publish(request: Request): return service.publish_hotspots(actor(request))

    @app.get('/api/improvements')
    def drafts(request: Request): return service.drafts(actor(request))

    @app.post('/api/improvements')
    def draft(body: Topic, request: Request): return service.draft(actor(request), body.topic_id)

    @app.post('/api/improvements/{draft_id}/review')
    def review(draft_id: str, body: Review, request: Request): return service.review(actor(request), draft_id, body.approve)

    @app.get('/api/audit')
    def audit(request: Request): return service.audit_view(actor(request))

    dist = ROOT / 'frontend/dist'
    if dist.exists():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')
        @app.get('/')
        def index(): return FileResponse(dist / 'index.html')
    else:
        @app.get('/')
        def index(): return {'message': 'Build frontend first. See README.md', 'docs': '/docs'}
    return app
