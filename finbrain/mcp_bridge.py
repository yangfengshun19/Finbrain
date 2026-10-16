"""Local stdio MCP bridge (2025-03-26). Never prints credentials or log text to stdout."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TOOLS = [
    ('ask_knowledge', 'Search enterprise knowledge accessible to the current identity; return a cited answer and evidence.', '/questions', 'POST', {'question': {'type': 'string', 'minLength': 1, 'maxLength': 2000}}, ['question']),
    ('get_my_briefing', 'Get the proactive work briefing for the current identity.', '/briefings', 'GET', {}, []),
    ('get_event_context', 'Read one source resource authorized for the current identity; missing and denied resources both return unavailable.', '/resources/', 'GET', {'resource_id': {'type': 'string'}}, ['resource_id']),
    ('get_knowledge_hotspots', 'Get published, authorized aggregate hotspots without raw queries or user details.', '/hotspots', 'GET', {}, []),
    ('submit_answer_feedback', 'Record whether one of your own answers resolved your question.', '/feedback', 'POST', {'query_id': {'type': 'string'}, 'resolved': {'type': 'boolean'}}, ['query_id', 'resolved']),
    ('draft_knowledge_improvement', 'Create an improvement draft for a topic you own; this does not approve or publish it.', '/improvements', 'POST', {'topic_id': {'type': 'string', 'enum': ['payment_guide', 'settlement_guide']}}, ['topic_id']),
]


def call_tool(name, args):
    tool = next((t for t in TOOLS if t[0] == name), None)
    if not tool:
        raise ValueError('Unknown tool')
    _, _, path, method, properties, required = tool
    if not isinstance(args, dict) or set(args) - set(properties) or any(k not in args for k in required):
        raise ValueError('Invalid tool arguments')
    for key, value in args.items():
        expected = properties[key]['type']
        if (expected == 'string' and not isinstance(value, str)) or (expected == 'boolean' and not isinstance(value, bool)):
            raise ValueError('Invalid argument type')
        if isinstance(value, str) and len(value) > 2000:
            raise ValueError('Argument too long')
    if name == 'get_event_context':
        path += urllib.parse.quote(args['resource_id'], safe='')
    base = os.getenv('FINBRAIN_URL', 'http://127.0.0.1:8765').rstrip('/')
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost'):
        raise ValueError('This bridge only supports a loopback demo server')
    token = os.getenv('FINBRAIN_TOKEN', '')
    if not token:
        raise ValueError('Configure FINBRAIN_TOKEN from your local FinBrain session')
    req = urllib.request.Request(base + '/api' + path, method=method,
        data=json.dumps(args).encode() if method == 'POST' else None,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'X-FinBrain-Client': '1'})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try: message = json.load(exc).get('detail', 'Request unavailable')
        except Exception: message = 'Request unavailable'
        raise ValueError(str(message)) from None
    except urllib.error.URLError:
        raise ValueError('Local FinBrain server unavailable') from None


def main():
    initialized = False
    negotiated = False
    for line in sys.stdin:
        request = None
        try:
            if len(line) > 1_000_000: raise ValueError('Message too large')
            request = json.loads(line)
            if not isinstance(request, dict) or request.get('jsonrpc') != '2.0': raise ValueError('Invalid JSON-RPC request')
            method = request.get('method')
            if method == 'notifications/initialized' and negotiated:
                initialized = True
                continue
            if 'id' not in request:
                continue
            if method == 'initialize':
                negotiated = True
                result = {'protocolVersion': '2025-03-26', 'capabilities': {'tools': {'listChanged': False}},
                          'serverInfo': {'name': 'finbrain-local', 'version': '0.1.0'},
                          'instructions': 'Tools run as the configured token identity. Never infer hidden resources. Drafts require human review in the web app.'}
            elif method == 'ping':
                result = {}
            elif not initialized:
                raise ValueError('Initialize the session first')
            elif method == 'tools/list':
                result = {'tools': [{'name': t[0], 'description': t[1], 'inputSchema': {'type': 'object', 'properties': t[4], 'required': t[5], 'additionalProperties': False}} for t in TOOLS]}
            elif method == 'tools/call':
                try:
                    params = request.get('params', {})
                    value = call_tool(params.get('name'), params.get('arguments', {}))
                    result = {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}], 'isError': False}
                except ValueError as exc:
                    result = {'content': [{'type': 'text', 'text': str(exc)}], 'isError': True}
            else:
                print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32601, 'message': 'Method not found'}}), flush=True)
                continue
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except Exception:
            response = {'jsonrpc': '2.0', 'id': request.get('id') if isinstance(request, dict) else None,
                        'error': {'code': -32600, 'message': 'Invalid request or lifecycle state'}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    main()
