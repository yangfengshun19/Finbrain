"""Exercise the actual stdio bridge against a running loopback API. No secrets printed."""
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
base = os.getenv('FINBRAIN_URL', 'http://127.0.0.1:8765').rstrip('/')
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def post(path, payload):
    request = urllib.request.Request(base + '/api' + path, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','X-FinBrain-Client':'1'})
    with opener.open(request, timeout=15) as response:
        return json.load(response)


post('/demo/login', {'user_id':'U02'})
token = post('/me/tool-token', {})['token']
messages = [
    {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'finbrain-smoke','version':'1'}}},
    {'jsonrpc':'2.0','method':'notifications/initialized'},
    {'jsonrpc':'2.0','id':2,'method':'tools/list'},
    {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'get_my_briefing','arguments':{}}},
    {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'ask_knowledge','arguments':{'question':'SL16'}}},
]
environment = {**os.environ, 'FINBRAIN_TOKEN':token, 'FINBRAIN_URL':base}
result = subprocess.run([sys.executable, str(ROOT/'mcp_bridge.py')], input='\n'.join(json.dumps(m) for m in messages)+'\n', encoding='utf-8', capture_output=True, env=environment, timeout=60)
assert result.returncode == 0, 'Bridge process failed'
rows = [json.loads(line) for line in result.stdout.splitlines()]
assert len(rows) == 4
assert len(rows[1]['result']['tools']) == 6
assert rows[2]['result']['isError'] is False
assert rows[3]['result']['isError'] is False
answer = json.loads(rows[3]['result']['content'][0]['text'])
assert answer['evidence'] == [], 'Ben must not receive private Slack evidence'
assert 'CANARY_INCIDENT' not in json.dumps(answer)
print('PASS: initialize, six tool schemas, live briefing, live permission-filtered query. Credentials not printed.')
