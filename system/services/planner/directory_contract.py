"""Shared comparisons between a portable declaration and a local adopted AU."""
import hashlib
import json

CONTRACT_FIELDS = ('id', 'version', 'kind', 'purpose', 'inputs', 'outputs', 'constraints')
BINDING_FIELDS = (*CONTRACT_FIELDS, 'agent_id', 'identity', 'endpoint', 'a2a_endpoint',
                  'agent_card_url', 'provenance')


def digest_fields(card, fields):
    return hashlib.sha256(json.dumps({key: card.get(key) for key in fields}, sort_keys=True).encode()).hexdigest()


def fingerprint(card):
    return digest_fields(card, CONTRACT_FIELDS)


def binding_fingerprint(card):
    # Lifecycle remains a live local decision, never inherited from Directory.
    return digest_fields(card, BINDING_FIELDS)


def bind_records(records, local_cards):
    """Return only locally adopted AUs whose current binding was retrieved from DIR.

    Endpoints always come from the local card; an external record cannot redirect
    an invocation or approve itself. Tools remain local, as they are not AUs.
    """
    local = {card['id']: card for card in local_cards if card.get('id')}
    accepted = {}
    excluded = []
    for item in records:
        record, cid = item['record'], item['cid']
        annotations = record.get('annotations') or {}
        identifier = annotations.get('aoa/capability-id')
        card = local.get(identifier)
        reason = None
        if not card or card.get('kind') != 'au':
            reason = 'not a locally adopted AU'
        elif (card.get('lifecycle') or {}).get('status') != 'approved':
            reason = 'not lifecycle-approved'
        elif annotations.get('aoa/binding-sha256') != binding_fingerprint(card):
            reason = 'published contract or runtime binding is stale'
        elif not any(module.get('name') == 'integration/a2a'
                     and (module.get('data') or {}).get('card_data', {}).get('url') == card.get('a2a_endpoint')
                     and any(skill.get('id') == identifier for skill in
                             (module.get('data') or {}).get('card_data', {}).get('skills', []))
                     for module in record.get('modules', [])):
            reason = 'A2A module does not describe the adopted capability'
        if reason:
            excluded.append({'capability': identifier, 'cid': cid, 'reason': reason})
        elif identifier not in accepted:
            accepted[identifier] = {**card, 'discovery_evidence': {
                'source': 'agntcy-directory', 'cid': cid, 'record_name': record.get('name'),
                'binding_sha256': annotations['aoa/binding-sha256'],
                'local_adoption_checked': True, 'publisher_identity_verified': False,
            }}
    cards = list(accepted.values()) + [card for card in local_cards if card.get('kind') == 'tool']
    missing = [card['id'] for card in local_cards if card.get('kind') == 'au'
               and (card.get('lifecycle') or {}).get('status') == 'approved' and card['id'] not in accepted]
    return cards, {'source': 'agntcy-directory', 'records_retrieved': len(records),
                   'accepted': [card['discovery_evidence'] | {'capability': card['id']} for card in accepted.values()],
                   'excluded': excluded, 'missing_current_publication': missing}
