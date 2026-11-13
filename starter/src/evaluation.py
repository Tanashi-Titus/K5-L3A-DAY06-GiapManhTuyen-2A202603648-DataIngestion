"""Evidence-based retrieval metrics; human audit remains separate."""
from collections import defaultdict
import unicodedata


def _normalize(s):
    return ' '.join(unicodedata.normalize('NFC', str(s)).casefold().split())


def evaluate_query(question, hits):
    golds = question.get('gold_alternatives') or [{'source_id': question['gold_source_id'], 'page': question['gold_page'], 'evidence_quote': question['evidence_quote']}]
    def matches(hit):
        return any(hit['document_id'] == g['source_id'] and hit['page'] == g['page'] and
                   _normalize(g['evidence_quote']) in _normalize(hit['text']) for g in golds)
    matched = [matches(h) for h in hits[:3]]
    return {'question': question, 'hits': hits[:3], 'hit1': bool(matched and matched[0]), 'hit3': any(matched)}


def summarize(traces):
    groups = defaultdict(list)
    for trace in traces: groups[(trace['strategy'], trace['question']['split'])].append(trace)
    return [{'strategy': key[0], 'split': key[1], 'n': len(items),
             'hit1_n': sum(t['hit1'] for t in items), 'hit3_n': sum(t['hit3'] for t in items),
             'hit1': sum(t['hit1'] for t in items)/len(items), 'hit3': sum(t['hit3'] for t in items)/len(items)}
            for key,items in sorted(groups.items())]
