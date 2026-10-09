"""Apply one reviewed deck adaptation atomically, preserving owner edits/history.

This dated migration is not a recurring pitch generator. It requires the exact
reviewed source hashes and previous pitch versions; later edits cause a conflict.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from founder_os.pitch_studio import PitchConflict, PitchStudio
from founder_os.store import Store, digest, now

PACK = ROOT / 'seed-data/pitch-deck-aligned-2026-10-09.json'
EXTRACTION = ROOT / 'reports/latest-final-decks-2026-10-09.json'
MANIFEST = ROOT / 'reports/pitch-deck-alignment-2026-10-09-manifest.json'


def canonical_state(store):
    return digest(store.rows('SELECT * FROM claims ORDER BY id'))


def apply(store):
    pack_text = PACK.read_text(encoding='utf-8')
    pack = json.loads(pack_text)
    extracted = {d['path']: d for d in json.loads(EXTRACTION.read_text(encoding='utf-8'))}
    studio = PitchStudio(store)
    active = store.rows("SELECT v.pitch_id FROM pitch_documents d JOIN pitch_versions v ON v.id=d.current_version_id WHERE v.status!='archived'")
    if {r['pitch_id'] for r in active} != {p['pitch_id'] for p in pack['pitches']}:
        raise PitchConflict('Active pitches differ from the reviewed set. Review the new or archived drafts first.')

    deck_sources = []
    for source in pack['deck_sources']:
        path = Path(source['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise PitchConflict('The deck changed since review: ' + str(path))
        doc = extracted[source['path']]
        if doc['sha256'] != source['sha256']:
            raise PitchConflict('Extraction does not match the reviewed deck: ' + str(path))
        pages = doc.get('slides', doc.get('pages', []))
        text = json.dumps(pages, ensure_ascii=False)
        deck_sources.append((source, text))

    pending = []
    for draft in pack['pitches']:
        current = studio.detail(draft['pitch_id'])
        title = draft.get('title', draft['title_match'])
        locator = 'September 29 pitch deck, slides ' + ', '.join(map(str, draft['slides']))
        notes = draft['notes'] + '\n\nSource: ' + locator + '. Read the original deck for context; its plans, models and illustrative examples are not newly verified company facts.'
        if (current['title'], current['body'], current['notes']) == (title, draft['body'], notes):
            continue
        if current['id'] != draft['expected_version_id']:
            raise PitchConflict('Preserving newer edits to ' + current['title'] + '. Review rather than reapplying this migration.')
        pending.append((draft, current, title, notes, locator))
    if not pending:
        return {'state': 'unchanged', 'pitches_already_aligned': len(pack['pitches'])}
    if MANIFEST.exists():
        raise PitchConflict('An earlier migration receipt exists. Review it before applying another batch.')

    # Register references only. No deck bytes are copied or uploaded.
    source_ids = {}
    for source, text in deck_sources:
        source_ids[Path(source['path']).name] = store.import_source(
            source['path'], 'pitch_deck', 'REFERENCE_NOT_CANONICAL',
            expected_sha256=source['sha256'], text=text,
            extraction='slide_text_and_notes' if source['path'].endswith('.pptx') else 'pdf_page_text',
            document_date=pack['source_date'] if Path(source['path']).name in (pack['primary_deck'], pack['primary_pdf']) else '2026-09-27')
    editorial_source = store.import_source(PACK, 'pitch_editorial', 'REFERENCE_NOT_CANONICAL', text=pack_text, extraction='reviewed_deck_adaptations')
    preference_source = store.import_source(ROOT / 'PITCH_WRITING.md', 'owner_writing_preferences', 'WRITING_GUIDANCE_NOT_COMPANY_FACTS', text=(ROOT / 'PITCH_WRITING.md').read_text(encoding='utf-8'), extraction='owner_preferences')
    primary_sources = [source_ids[pack['primary_deck']], source_ids[pack['primary_pdf']], editorial_source, preference_source]
    prepared = []
    for draft, old, title, notes, locator in pending:
        fields = studio._fields({**old, 'title': title, 'body': draft['body'], 'notes': notes,
            'status': 'draft', 'sources': list(dict.fromkeys(old['sources'] + primary_sources)),
            'change_note': 'Latest September 29 deck and owner writing preferences - October 9'})
        prepared.append((draft, old, fields, locator))

    changes = []
    with store.transaction():
        truth_before = canonical_state(store)
        live_active = store.rows("SELECT v.pitch_id FROM pitch_documents d JOIN pitch_versions v ON v.id=d.current_version_id WHERE v.status!='archived'")
        if {r['pitch_id'] for r in live_active} != {p['pitch_id'] for p in pack['pitches']}:
            raise PitchConflict('The active pitch set changed during review. No revisions were applied.')
        for draft, old, fields, locator in prepared:
            live = store.one('SELECT current_version_id FROM pitch_documents WHERE pitch_id=?', (old['pitch_id'],))
            if live['current_version_id'] != old['id']:
                raise PitchConflict('A pitch changed during review. No pitch revisions were applied.')
        for draft, old, fields, locator in prepared:
            vid = studio._version(old['pitch_id'], fields, old['id'])
            for source in primary_sources[:2]:
                store.import_receipt(source, 'pitch_version', vid, locator, 'Audience-specific working adaptation; no company fact promotion')
            changes.append({'pitch_id': old['pitch_id'], 'title': fields['title'],
                'before_version_id': old['id'], 'after_version_id': vid,
                'source_slides': draft['slides'], 'source_versions': primary_sources,
                'original_version_sha256': digest(store.one('SELECT * FROM pitch_versions WHERE id=?', (old['id'],)))})
        if canonical_state(store) != truth_before:
            raise RuntimeError('Canonical company facts unexpectedly changed')
        store.log('pitch.deck_alignment', 'owner_requested_editorial', {'revision': pack['revision'], 'changes': changes})

    manifest = {'revision': pack['revision'], 'completed_at': now(), 'changes': changes,
        'deck_sources': pack['deck_sources'], 'registered_sources': source_ids,
        'originals_modified': False, 'canonical_facts_changed': False,
        'external_submissions': 0, 'old_versions_retained': True}
    # Never replace an earlier migration receipt.
    with MANIFEST.open('x', encoding='utf-8') as output:
        output.write(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return {'state': 'saved', 'pitches_updated': len(changes), 'manifest': str(MANIFEST)}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    store = Store(ROOT / 'data/founder.sqlite')
    try:
        print(json.dumps(apply(store), ensure_ascii=False))
    finally:
        store.close()
