"""Application services shared by HTTP and MCP. All source reads reauthorize."""
import hashlib
import secrets
import threading
import time
from functools import wraps
from datetime import datetime

from .answers import answer
from .knowledge import Knowledge, reference

TOPICS = {
    'payment_guide': {'name': 'Payment operations and incident guidance', 'anchor': 'CF01', 'keywords': ['payment', 'runbook', 'response', 'pay-', 'payment', 'runbook'], 'owner': 'U01'},
    'settlement_guide': {'name': 'Settlement and reconciliation guidance', 'anchor': 'CF05', 'keywords': ['settlement', 'reconciliation', 'settlement'], 'owner': 'U03'},
}


def serialized(method):
    """One local process: timeline mutations and permissioned reads are atomic."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return wrapped


class ServiceError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Service:
    def __init__(self, store):
        self.store = store
        self.knowledge = Knowledge(store)
        self.lock = threading.RLock()

    def authenticate(self, token):
        rows = self.store.all('SELECT * FROM sessions WHERE token_hash=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time()))
        if not rows:
            raise ServiceError(401, 'Select a demo identity first.')
        uid = rows[0]['uid']
        self.active(uid)
        return uid

    def active(self, uid):
        state = self.knowledge.state()
        if not state['accounts'].get(uid, {}).get('active'):
            raise ServiceError(403, 'This demo account is disabled. Switch identities.')
        return state

    def login(self, uid):
        self.active(uid)
        token = secrets.token_urlsafe(36)
        self.store.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), uid, time.time() + 8 * 3600))
        return token

    @serialized
    def me(self, uid):
        state = self.active(uid)
        return {**state['users'][uid], 'snapshot': state['snapshot'], 'as_of': state['as_of'],
                'memberships': sorted(self.knowledge.member_of(state, uid)),
                'can_audit': reference.can_audit(state, uid, 'PAY-042'),
                'can_improve': any(t['owner'] == uid for t in TOPICS.values()),
                'visible_count': len(self.knowledge.visible(state, uid))}

    def log(self, uid, action, payload, state=None):
        state = state or self.knowledge.state()
        self.store.audit({'user_id': uid, 'action': action, 'snapshot': state['snapshot'], 'timestamp': state['as_of'], 'payload': payload})

    def ask(self, uid, question):
        if not question.strip() or len(question) > 2000:
            raise ServiceError(400, 'Enter a question containing 1 to 2,000 characters.')
        with self.lock:
            state = self.active(uid)
            evidence, decisions = self.knowledge.search(state, uid, question)
            result = answer(question, evidence)
            # Lock serializes demo timeline changes and answer generation.
            current = self.knowledge.state()
            if any(not self.knowledge.allowed(current, uid, e['id']) for e in evidence):
                raise ServiceError(409, 'Permissions have changed. Please retry.')
            qid = secrets.token_hex(12)
            response = {**result, 'id': qid, 'question': question, 'evidence': evidence,
                        'snapshot': state['snapshot'], 'as_of': state['as_of']}
            self.store.execute('INSERT INTO queries VALUES (?,?,?,?)', (qid, uid, state['snapshot'], self.store.seal(response)))
            self.log(uid, 'question', {'question': question, 'decisions': decisions, 'response': response}, state)
            topic = self.topic_for(state, uid, question, evidence)
            if topic:
                window = state['as_of'][:10]
                self.store.execute('INSERT OR IGNORE INTO analytics(topic,window,subject,unresolved) VALUES (?,?,?,0)', (topic, window, self.store.pseudonym(uid, window)))
            return response

    def topic_for(self, state, uid, question, evidence):
        if not evidence:
            return None
        for key, topic in TOPICS.items():
            if any(w in question.lower() for w in topic['keywords']) and self.knowledge.allowed(state, uid, topic['anchor']):
                return key
        return None

    @serialized
    def feedback(self, uid, qid, resolved):
        rows = self.store.all('SELECT * FROM queries WHERE id=? AND uid=?', (qid, uid))
        if not rows:
            raise ServiceError(404, 'Record unavailable.')
        state = self.active(uid)
        response = self.store.unseal(rows[0]['payload'])
        topic = self.topic_for(state, uid, response['question'], response['evidence'])
        # Late feedback stays in the original fixed window; published releases never change.
        window = response['as_of'][:10]
        if topic:
            self.store.execute('UPDATE analytics SET unresolved=? WHERE topic=? AND window=? AND subject=?', (int(not resolved), topic, window, self.store.pseudonym(uid, window)))
        self.log(uid, 'feedback', {'query_id': qid, 'resolved': resolved}, state)
        return {'saved': True}

    @serialized
    def resource(self, uid, rid):
        state = self.active(uid)
        evidence = self.knowledge.evidence(state, uid, [rid])
        if not evidence:
            raise ServiceError(404, 'Resource unavailable.')
        self.log(uid, 'resource_read', {'resource_ids': [rid]}, state)
        return evidence[0]

    @serialized
    def briefings(self, uid):
        state = self.active(uid)
        visible = self.knowledge.visible(state, uid)
        reads = {r['rid']: r['version'] for r in self.store.all('SELECT * FROM reads WHERE uid=?', (uid,))}
        groups = self.knowledge.member_of(state, uid)
        candidates = []
        for resource in visible:
            if resource['scenario_id'] not in ('PAY-042', 'SET-019'):
                continue
            # Historical guesses remain available in the timeline, but do not
            # compete with a confirmed conclusion the same user can now read.
            if resource['id'] in ('SL16', 'SL17', 'GD10') and self.knowledge.allowed(state, uid, 'CF12'):
                continue
            # Topic relevance and recency, no model-decided authorization/priority.
            urgency = 2 if resource['id'] in ('JR13', 'JR15') and state['snapshot'] < 'T10' else 0
            current_duty = 'group:incident' in groups and resource['source'] in ('jira', 'slack')
            importance = 2 if resource['id'] in ('CF01', 'CF12', 'JR13', 'JR15', 'JR16', 'GD12') else 0
            changed = resource['content_version'] > 1 or resource['created_at'] > self.knowledge.dataset['baseline']['as_of']
            score = urgency * 5 + importance * 3 + int(current_duty)*3 + int(changed)*2
            if score < 4:
                continue
            reasons = []
            if urgency: reasons.append('The incident is unresolved; follow up on its status')
            if current_duty: reasons.append('You are a current incident responder')
            if importance: reasons.append('Related to a key process or fix status')
            if changed: reasons.append('The resource has a substantive update')
            seen = reads.get(resource['id'], 0) >= resource['content_version']
            candidates.append({'id': resource['id'], 'title': resource['title'], 'summary': resource['body'],
                               'priority': 'urgent' if urgency else ('action' if current_duty else 'awareness'),
                               'score': score, 'reasons': reasons, 'read': seen, 'source': resource['source'],
                               'version': resource['content_version'], 'updated_at': resource['updated_at'],
                               'evidence_ids': [resource['id']],
                               'suggestion': 'Check current evidence, the owner, and next steps.' if urgency else 'Review the latest version; marking it read does not complete the task.'})
        candidates.sort(key=lambda c: (c['read'], -c['score'], -int(c['version']), c['id']))
        buckets = {}
        for card in candidates:
            rid = card['id']
            key = ('repair' if rid in ('JR01', 'JR13', 'JR15', 'JR16') else
                   'root_cause' if rid in ('CF12', 'SL18') else
                   'coordination' if rid in ('SL15', 'SL20') else rid)
            if key not in buckets:
                buckets[key] = card
            else:
                parent = buckets[key]
                parent['evidence_ids'].append(rid)
                parent['read'] = parent['read'] and card['read']
        cards = list(buckets.values())[:8]
        self.log(uid, 'briefing_read', {'resource_ids': [c['id'] for c in cards]}, state)
        return {'cards': cards, 'visible_count': len(visible), 'as_of': state['as_of'], 'snapshot': state['snapshot'],
                'on_call': 'group:incident' in groups, 'source_count': len({r['source'] for r in visible})}

    @serialized
    def mark_read(self, uid, rid):
        resource = self.resource(uid, rid)
        card = next((c for c in self.briefings(uid)['cards'] if c['id'] == rid), None)
        state = self.knowledge.state()
        for evidence_id in card['evidence_ids'] if card else [rid]:
            self.store.execute('INSERT OR REPLACE INTO reads VALUES (?,?,?)', (uid, evidence_id, state['resources'][evidence_id]['content_version']))
        return {'saved': True}

    @serialized
    def publish_hotspots(self, uid):
        state = self.active(uid)
        today = state['as_of'][:10]
        # Only explicit knowledge owners can publish their own preapproved topics.
        published = 0
        for tid, topic in TOPICS.items():
            if topic['owner'] != uid or not self.knowledge.allowed(state, uid, topic['anchor']):
                continue
            for row in self.store.all('SELECT window, COUNT(*) AS contributors, SUM(unresolved) AS unresolved FROM analytics WHERE topic=? AND window<? GROUP BY window', (tid, today)):
                if row['contributors'] < 5:
                    continue
                window = row['window']
                payload = {'topic_id': tid, 'name': topic['name'], 'window': window, 'heat': 'high' if row['contributors'] >= 8 else 'medium',
                           'trend': 'not_compared', 'reasons': ['Multiple people need knowledge on this topic'],
                           'suggestion': 'Review existing instructions for completeness and clarity; query interest does not establish an incident.',
                           'privacy': 'Fixed daily windows; at least 5 people; capped individual contributions; no identities or raw questions'}
                if row['unresolved'] >= 5:
                    payload['reasons'].append('Multiple people explicitly reported unresolved questions')
                cursor = self.store.execute('INSERT OR IGNORE INTO releases VALUES (?,?,?)', (tid, window, self.store.seal(payload)))
                published += max(cursor.rowcount, 0)
        self.log(uid, 'hotspot_publish', {'published': published}, state)
        return {'published': published, 'message': 'Fixed windows checked. Only aggregates meeting publication rules will appear.'}

    @serialized
    def hotspots(self, uid):
        state = self.active(uid)
        items = []
        for row in self.store.all('SELECT * FROM releases WHERE window<? ORDER BY window DESC', (state['as_of'][:10],)):
            topic = TOPICS.get(row['topic'])
            if topic and self.knowledge.allowed(state, uid, topic['anchor']):
                items.append(self.store.unseal(row['payload']))
        return {'items': items, 'can_publish': any(t['owner'] == uid and self.knowledge.allowed(state, uid, t['anchor']) for t in TOPICS.values()),
                'note': 'Unpublished windows, sample counts, and individual contributions are hidden. Threshold aggregation is not a formal anonymity guarantee.'}

    @serialized
    def draft(self, uid, topic_id):
        state = self.active(uid)
        topic = TOPICS.get(topic_id)
        if not topic or topic['owner'] != uid or not self.knowledge.allowed(state, uid, topic['anchor']):
            raise ServiceError(403, 'You do not have permission to maintain this topic.')
        rid = topic['anchor']
        resource = state['resources'][rid]
        text = ('\n\nStatus interpretation addendum: a code merge does not mean deployment is complete; a completed deployment does not mean all follow-up validation is finished. '
                'Before acting, check the latest issue status, runbook version, and on-call owner. If evidence is insufficient, contact the owner rather than substituting assumptions for confirmed findings.')
        draft_id = secrets.token_hex(10)
        payload = {'id': draft_id, 'topic_id': topic_id, 'title': topic['name'] + ' · Improvement proposal', 'resource_id': rid,
                   'base_version': resource['content_version'], 'base_body': resource['body'],
                   'proposed_body': resource['body'] + text,
                   'reason': 'Add general status interpretation guidance to the existing document; no raw employee queries are quoted.',
                   'mode': 'template_draft', 'status': 'pending'}
        self.store.execute('INSERT INTO drafts VALUES (?,?,?,?,?)', (draft_id, uid, state['snapshot'], 'pending', self.store.seal(payload)))
        self.log(uid, 'draft_created', {'draft_id': draft_id, 'resource_ids': [rid]}, state)
        return payload

    @serialized
    def drafts(self, uid):
        state = self.active(uid)
        result = []
        for row in self.store.all('SELECT * FROM drafts WHERE owner=? AND snapshot<=?', (uid, state['snapshot'])):
            value = self.store.unseal(row['payload'])
            if self.knowledge.allowed(state, uid, value['resource_id']):
                result.append({**value, 'status': row['status']})
        return {'items': result}

    def review(self, uid, draft_id, approve):
        with self.lock:
            state = self.active(uid)
            rows = self.store.all('SELECT * FROM drafts WHERE id=? AND owner=? AND snapshot<=?', (draft_id, uid, state['snapshot']))
            if not rows or rows[0]['status'] != 'pending': raise ServiceError(404, 'Pending draft unavailable.')
            value = self.store.unseal(rows[0]['payload'])
            if not self.knowledge.allowed(state, uid, value['resource_id']): raise ServiceError(403, 'You currently lack permission to maintain this resource.')
            resource = state['resources'][value['resource_id']]
            if approve:
                if resource['content_version'] != value['base_version'] or resource['body'] != value['base_body']:
                    raise ServiceError(409, 'The source resource has changed. Generate a new draft.')
                source_version = reference.materialize(self.knowledge.dataset, state['snapshot'])['resources'][value['resource_id']]['content_version']
                overlay = {'body': value['proposed_body'], 'content_version': resource['content_version'] + 1, 'updated_at': state['as_of'], '_base_source_version': source_version}
                self.store.execute('INSERT OR REPLACE INTO overlays VALUES (?,?,?)', (value['resource_id'], state['snapshot'], self.store.seal(overlay)))
            self.store.execute('UPDATE drafts SET status=? WHERE id=?', ('approved' if approve else 'rejected', draft_id))
            self.log(uid, 'draft_reviewed', {'draft_id': draft_id, 'approved': approve, 'resource_ids': [value['resource_id']]}, state)
            return {'status': 'approved' if approve else 'rejected', 'message': 'The local mock resource has been updated.' if approve else 'This draft was rejected.'}

    @serialized
    def timeline(self, uid):
        state = self.active(uid)
        # Build from authorized source versions, never expose raw global event titles.
        items = []
        for event in self.knowledge.dataset['events']:
            if event['snapshot'] > state['snapshot']: break
            prior = reference.materialize(self.knowledge.dataset, event['snapshot'])
            for change in event['changes']:
                rid = change.get('resource_id') or change.get('resource', {}).get('id')
                if rid and self.knowledge.allowed(state, uid, rid) and rid in prior['resources']:
                    resource = prior['resources'][rid]
                    if resource['deleted']: continue
                    items.append({'snapshot': event['snapshot'], 'at': event['effective_at'], 'resource_id': rid,
                                  'title': resource['title'], 'summary': resource['body'], 'version': resource['content_version'], 'source': resource['source']})
        self.log(uid, 'timeline_read', {'resource_ids': list({e['resource_id'] for e in items})}, state)
        return {'items': list(reversed(items))[:24]}

    @serialized
    def action_check(self, uid, rid, version):
        current = self.resource(uid, rid)
        return {'resource': current, 'outdated': version != current['content_version'],
                'message': 'The cited version has changed. Check the latest content before acting.' if version != current['content_version'] else 'The cited version matches the current version; this does not certify that an action is safe.'}

    @serialized
    def audit_view(self, uid):
        state = self.active(uid)
        if not reference.can_audit(state, uid, 'PAY-042'):
            raise ServiceError(403, 'You do not have audit access to the current incident.')
        items = []
        for row in self.store.all('SELECT * FROM audit ORDER BY seq DESC LIMIT 300'):
            value = self.store.unseal(row['payload'])
            if value['snapshot'] > state['snapshot']: continue
            # Cross-scope questions/answers are intentionally excluded from this scoped viewer.
            payload = value['payload']
            ids = list(payload.get('resource_ids', []))
            ids += [e['id'] for e in payload.get('response', {}).get('evidence', [])]
            ids += [d['resource_id'] for d in payload.get('decisions', [])]
            if not ids: continue
            all_resources = reference.materialize(self.knowledge.dataset, 'T14')['resources']
            if any(all_resources.get(rid, {}).get('scenario_id') != 'PAY-042' for rid in ids): continue
            # Return restricted audit metadata, not arbitrary raw query text or source excerpts.
            items.append({'sequence': row['seq'], 'user_id': value['user_id'], 'action': value['action'],
                          'timestamp': value['timestamp'], 'snapshot': value['snapshot'],
                          'resource_ids': sorted(set(ids)), 'decisions': payload.get('decisions', []), 'hash': row['hash'][:16]})
        return {'items': items[:80], 'chain_valid': self.store.verify_audit(),
                'note': 'Log contents are encrypted and checked with an HMAC chain. A local key is not an independent external anchor and cannot detect every tail deletion. This view shows only metadata within the PAY-042 scope.'}

    def demo_seed(self):
        with self.lock:
            if self.store.setting('seeded') == 'yes':
                return {'message': 'Demo help requests have already been generated; no repeat import is needed.'}
            old = self.store.setting('snapshot', 'T10')
            previous_mode = __import__('os').environ.get('FINBRAIN_ANSWER_MODE')
            __import__('os').environ['FINBRAIN_ANSWER_MODE'] = 'extractive'
            try:
                self.store.set_setting('snapshot', 'T10')
                for uid in ('U01', 'U02', 'U03', 'U04', 'U05', 'U06'):
                    result = self.ask(uid, 'How does the payment runbook distinguish a merged fix from completed deployment?')
                    self.feedback(uid, result['id'], False)
                self.store.set_setting('seeded', 'yes')
            finally:
                self.store.set_setting('snapshot', old)
                if previous_mode is None: __import__('os').environ.pop('FINBRAIN_ANSWER_MODE', None)
                else: __import__('os').environ['FINBRAIN_ANSWER_MODE'] = previous_mode
            return {'message': 'Simulated help requests from 6 fictional employees at T10 are complete. Switch to T13 and publish the previous day hotspots as Alice.'}
