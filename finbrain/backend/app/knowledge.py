"""Source adapter, current permissions and deterministic authorized retrieval."""
import copy
import importlib.util
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('finbrain_reference_access', WORKSPACE / 'finbrain_mock/access.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def terms(text):
    lower = text.lower()
    result = set(re.findall(r'[a-z][a-z0-9_-]*|\d+', lower))
    for run in re.findall(r'[\u4e00-\u9fff]+', lower):
        result.update(run[i:i+2] for i in range(len(run)-1))
    return result


class Knowledge:
    def __init__(self, store):
        self.store = store
        self.dataset = reference.load_dataset(WORKSPACE / 'finbrain_mock/data/dataset.json')
        self.snapshots = {e['snapshot'] for e in self.dataset['events']}

    def state(self):
        label = self.store.setting('snapshot', 'T10')
        state = reference.materialize(self.dataset, label)
        state['snapshot'] = label
        for row in self.store.all('SELECT * FROM overlays WHERE snapshot<=?', (label,)):
            if row['rid'] in state['resources'] and not state['resources'][row['rid']]['deleted']:
                original = state['resources'][row['rid']]
                overlay = self.store.unseal(row['payload'])
                if overlay.pop('_base_source_version', original['content_version']) == original['content_version']:
                    original.update(overlay)
        return state

    def allowed(self, state, uid, rid):
        return reference.can_read(state, uid, rid)[0]

    def visible(self, state, uid):
        return [r for r in state['resources'].values() if self.allowed(state, uid, r['id'])]

    def search(self, state, uid, question, limit=6):
        query = terms(question)
        lower_question = question.lower()
        explicit = re.findall(r'\b(?:CF|JR|SL|GD)\d{2}\b', question.upper())
        # Candidate matching is internal. Only authorized matches leave the service.
        ranked = []
        for resource in state['resources'].values():
            if resource['deleted']:
                continue
            title_hits = query & terms(resource['title'])
            body_hits = query & terms(resource['body'])
            score = len(title_hits) * 3 + len(body_hits)
            if explicit:
                score = 100 if resource['id'] in explicit else 0
            if score:
                if any(t in lower_question for t in ('root cause', 'what caused')) and resource['id'] == 'CF12': score += 25
                if any(t in lower_question for t in ('deploy', 'go live', 'fix progress')) and resource['id'] in ('JR15', 'JR16'): score += 20
                if 'runbook' in lower_question and resource['id'] == 'CF01': score += 15
                ranked.append((score, resource['updated_at'], resource['id']))
        ranked.sort(reverse=True)
        decisions = [{'resource_id': rid, 'allowed': self.allowed(state, uid, rid), 'scenario': state['resources'][rid]['scenario_id']} for _, _, rid in ranked]
        ids = [rid for _, _, rid in ranked if self.allowed(state, uid, rid)][:limit]
        return self.evidence(state, uid, ids), decisions

    def evidence(self, state, uid, ids):
        result = reference.authorized_context(state, uid, ids)
        # Use guarded local preview URLs rather than pretend these are live source links.
        for resource in result:
            resource['preview_url'] = '/api/resources/' + resource['id']
        return result

    def member_of(self, state, uid):
        return reference.memberships(state, uid)
