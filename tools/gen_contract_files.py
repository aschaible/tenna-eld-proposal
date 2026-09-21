#!/usr/bin/env python3
"""Generate the OpenAPI spec and the Postman collection for the proposed
Tenna data contracts (architecture.html#data-contracts) from one definition,
so the two files cannot drift apart. Run: python3 tools/gen_contract_files.py"""
import json, os, uuid

OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'api')
VERSION = '0.1.0-proposal'

def S(t, desc, **kw):
    d = {'type': t, 'description': desc}; d.update(kw); return d
def N(d):  # nullable
    d = dict(d); d['nullable'] = True; return d

SCHEMAS = {
  'TokenClaims': {
    'type': 'object',
    'description': 'T1 Identity. Not an endpoint: the claims the ELD relies on in the Cognito JWT that every call sends. '
                   'Session 30 days with hourly refresh; the ELD prompts re-sign-in at day 25.',
    'required': ['sub', 'username', 'account_id', 'roles', 'licenses', 'exp', 'iat'],
    'properties': {
      'sub': S('string', 'Tenna user id. Stored as driver_id on every ELD event.'),
      'username': S('string', 'ELD username (Appendix A 7.18): the sign-in name. An email address is acceptable. '
                    'Never issued to a second person in the same account.', minLength=4, maxLength=60),
      'account_id': S('string', 'The carrier. Every ELD row is scoped to it.'),
      'roles': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Driver, supervisor, mechanic.'},
      'licenses': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Must include "eld", or the T8 entitlement flag is used instead.'},
      'exp': S('integer', 'Expiry, epoch seconds.'),
      'iat': S('integer', 'Issued at, epoch seconds.'),
      'acting_as': N(S('string', 'OPEN. Present only when Tenna staff are viewing as a customer user. The ELD treats the session as read-only (4.1.2).')),
    },
    'example': {'sub': 'usr_8f21c4', 'username': 'malvarez', 'account_id': 'acc_0413', 'roles': ['driver'],
                'licenses': ['eld'], 'iat': 1758067200, 'exp': 1760659200},
  },
  'Person': {
    'type': 'object',
    'required': ['id', 'username', 'first_name', 'last_name', 'is_driver', 'status', 'roles'],
    'properties': {
      'id': S('string', 'Join key to every ELD row.'),
      'username': S('string', 'ELD username (7.18), same value as the token claim.', minLength=4, maxLength=60),
      'first_name': S('string', 'First name (7.28). Required for everyone: the output file user list names each supervisor who requested an edit.'),
      'last_name': S('string', 'Last name (7.30).'),
      'is_driver': S('boolean', 'Who appears in the roster and may hold duty status. Sets ELD account type (7.13): D or S.'),
      'status': S('string', 'Rosters and pickers hide inactive people; past records still show their name.', enum=['active', 'inactive']),
      'exempt': N(S('boolean', 'Exempt driver per 4.3.3.1.2. Null means false.')),
      'exempt_annotation': N(S('string', 'Reason recorded with the exemption. Required when exempt is true.')),
      'cdl': N({'type': 'object', 'description': 'Required for drivers. Returned only to callers with eld.logs.read.',
                'required': ['number', 'state'],
                'properties': {'number': S('string', "Driver's license number (7.11)."),
                               'state': S('string', "Driver's license issuing state (7.10).", minLength=2, maxLength=2)}}),
      'roles': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Same vocabulary as the token.'},
      'email': N(S('string', 'Contact line on D23; needed if own-records delivery goes by email.')),
      'phone': N(S('string', 'Contact line only.')),
    },
  },
  'Account': {
    'type': 'object', 'required': ['id', 'name', 'usdot', 'address'],
    'properties': {
      'id': S('string', 'Stored as carrier_id on every ELD row.'),
      'name': S('string', 'Carrier name (7.2).'),
      'usdot': S('string', "Carrier's USDOT number (7.3).", pattern='^[0-9]{1,9}$'),
      'address': {'type': 'object', 'required': ['street', 'city', 'state', 'zip'],
                  'description': 'Carrier address on the roadside display and printed logs.',
                  'properties': {'street': {'type': 'string'}, 'city': {'type': 'string'},
                                 'state': {'type': 'string', 'minLength': 2, 'maxLength': 2}, 'zip': {'type': 'string'}}},
      'support_contact': N({'type': 'object', 'description': 'Who a driver calls at the carrier about the ELD (D25). Null hides the line.',
                            'properties': {'name': N({'type': 'string'}), 'phone': N({'type': 'string'}), 'email': N({'type': 'string'})}}),
    },
  },
  'Asset': {
    'type': 'object', 'required': ['id', 'name', 'vin', 'tracker'],
    'properties': {
      'id': S('string', 'Stored as asset_id on every event and link.'),
      'name': S('string', 'Fleet unit number; the CMV power unit number (7.4).'),
      'vin': S('string', 'CMV VIN of record (7.5). Cross-checked against the VIN the tracker reads.', minLength=17, maxLength=17),
      'category': N(S('string', 'Display only. Categories are per-account; the ELD never branches on it.')),
      'assigned_driver_id': N(S('string', "Tenna's driver-to-vehicle assignment, shown on W1. Display only.")),
      'tracker': N({'type': 'object', 'required': ['serial', 'model'],
                    'description': 'Null once the tracker is removed; the asset still resolves by id.',
                    'properties': {'serial': S('string', 'The join from a BLE scan to an asset.'),
                                   'model': S('string', "ELD-enabled means this is one of Tenna's two ELD tracker models."),
                                   'firmware_version': N(S('string', 'Null means unknown.'))}}),
      'trailer_number': N(S('string', 'Trailer number (7.42) if Tenna keeps it on the asset or DVIR record; otherwise the driver enters it on D2.')),
    },
  },
  'TrackerModel': {'type': 'object', 'required': ['model'],
                   'properties': {'model': S('string', 'A tracker model name that marks an asset as ELD-enabled.')}},
  'Site': {
    'type': 'object', 'required': ['id', 'name', 'type', 'geometry', 'updated_at'],
    'properties': {
      'id': S('string', 'Cache key.'), 'name': S('string', 'Shown on D9 when a yard move ends.'),
      'type': S('string', 'Only "yard" is read. Tenna names the site type that means a yard.'),
      'geometry': {'type': 'object', 'description': 'GeoJSON Polygon. A circle is accepted as centre plus radius if that is how Tenna stores it.',
                   'required': ['type', 'coordinates'],
                   'properties': {'type': {'type': 'string', 'enum': ['Polygon']},
                                  'coordinates': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}}}}},
      'updated_at': S('string', 'Refresh only what changed.', format='date-time'),
    },
  },
  'WorkOrder': {
    'type': 'object', 'required': ['id', 'number', 'asset_id'],
    'properties': {
      'id': S('string', 'Stored on the road test annotation.'),
      'number': S('string', 'Human reference shown on D27.'),
      'job_number': N(S('string', 'Job or project the work is under. Pre-fills the shipping document field (7.39) on D2.')),
      'asset_id': S('string', 'Must match the paired asset.'),
      'summary': N(S('string', 'Picker line.')),
      'assigned_to': N(S('string', "User id. Sorts the mechanic's own orders first.")),
    },
  },
  'DvirStatus': {
    'type': 'object', 'required': ['status', 'defects_open'],
    'description': 'Contract still to be written with Tenna; these are the fields D14 needs.',
    'properties': {
      'status': S('string', 'Which of the three states D14 draws.', enum=['not_started', 'started', 'submitted']),
      'inspection_id': N(S('string', 'Present when started or submitted.')),
      'submitted_at': N(S('string', 'Present when submitted.', format='date-time')),
      'defects_open': S('integer', 'Warns the driver before they drive; the ELD does not block.'),
      'shipping_document_number': N(S('string', "Shipping document number (7.39) if Tenna's DVIR flow includes it.")),
    },
  },
  'Entitlements': {
    'type': 'object', 'required': ['account_id', 'modules', 'permissions'],
    'properties': {
      'account_id': S('string', 'Must match the token.'),
      'modules': {'type': 'object', 'required': ['eld'], 'properties': {'eld': S('boolean', 'Sign-in gate.')}},
      'permissions': {'type': 'array', 'description': 'Each W screen checks one.',
                      'items': {'type': 'string', 'enum': ['eld.logs.read', 'eld.logs.propose_edit', 'eld.settings.write', 'eld.ud.assign', 'eld.transfer.request']}},
    },
  },
  'Error': {'type': 'object', 'required': ['error'], 'properties': {'error': {'type': 'string'}, 'message': {'type': 'string'}}},
}

MARIA = {'id': 'usr_8f21c4', 'username': 'malvarez', 'first_name': 'Maria', 'last_name': 'Alvarez', 'is_driver': True,
         'status': 'active', 'exempt': False, 'exempt_annotation': None, 'cdl': {'number': 'RE123456', 'state': 'OH'},
         'roles': ['driver'], 'email': 'm.alvarez@example.com', 'phone': None}
DAN = {'id': 'usr_5510', 'username': 'dokafor', 'first_name': 'Dan', 'last_name': 'Okafor', 'is_driver': False,
       'status': 'active', 'exempt': None, 'exempt_annotation': None, 'cdl': None, 'roles': ['mechanic'], 'email': None, 'phone': None}
UNIT218 = {'id': 'ast_2181', 'name': 'Unit 218', 'vin': '1FTFW1R63EFA84339', 'category': 'Pickup truck',
           'assigned_driver_id': 'usr_8f21c4',
           'tracker': {'serial': 'WQ-87X060680218', 'model': 'WQ-ELD', 'firmware_version': None}, 'trailer_number': None}

def q(name, desc, example=None, required=False, schema=None):
    return {'name': name, 'in': 'query', 'description': desc, 'required': required,
            'schema': schema or {'type': 'string'}, 'example': example}

# surface, folder title, path, summary, description, params, response schema ref, is_array, named requests [(name, query dict, example body)]
OPS = [
  ('T2', 'T2 People', '/eld/v1/people', 'List, batch-resolve or search people',
   'Three uses of one call. Roster: is_driver=true, paged (W1, W3, W15). Batch: ids, up to 200; keeps resolving '
   'inactive and departed users for as long as the ELD retains their records. Search: q, for the W16 assignment picker. '
   'Called by the ELD API on the server and by the phone at sign-in.',
   [q('ids', 'Comma-separated user ids, up to 200.', 'usr_8f21c4,usr_5510'), q('q', 'Name search.', 'alva'),
    q('is_driver', 'Roster filter.', True, schema={'type': 'boolean'}),
    q('status', 'active (default) or all.', 'active', schema={'type': 'string', 'enum': ['active', 'all']}),
    q('page', 'Page number, 1-based.', 1, schema={'type': 'integer', 'minimum': 1})],
   'Person', True,
   [('Driver roster (paged)', {'is_driver': 'true', 'page': '1'}, [MARIA]),
    ('Batch lookup by id', {'ids': 'usr_8f21c4,usr_5510'}, [MARIA, DAN]),
    ('Name search', {'q': 'alva'}, [MARIA])]),
  ('T3', 'T3 Org', '/eld/v1/account', "The caller's own account",
   'Account id comes from the token. Read at sign-in and cached for the day. No time zone or day start: those are ELD-owned.',
   [], 'Account', False,
   [('Get account', {}, {'id': 'acc_0413', 'name': 'Blue Ash Construction Co.', 'usdot': '3172584',
                         'address': {'street': '4400 Cooper Rd', 'city': 'Blue Ash', 'state': 'OH', 'zip': '45242'},
                         'support_contact': {'name': 'Fleet office', 'phone': '513-555-0142', 'email': 'fleet@example.com'}})]),
  ('T4', 'T4 Assets', '/eld/v1/assets', 'Find assets by tracker serial, ELD flag or id list',
   'tracker_serial: one asset, at pairing. eld=true: the pairing list, every ELD-enabled asset. ids: batch, up to 200; '
   'keeps resolving an asset after its tracker is removed or the asset is retired. Always returns an array.',
   [q('tracker_serial', 'Tracker serial from the BLE scan.', 'WQ-87X060680218'),
    q('eld', 'Only assets whose tracker is an ELD model.', True, schema={'type': 'boolean'}),
    q('ids', 'Comma-separated asset ids, up to 200.', 'ast_2181')],
   'Asset', True,
   [('By tracker serial (pairing)', {'tracker_serial': 'WQ-87X060680218'}, [UNIT218]),
    ('ELD-enabled assets (pairing list)', {'eld': 'true'}, [UNIT218]),
    ('Batch lookup by id', {'ids': 'ast_2181'}, [UNIT218])]),
  ('T4', 'T4 Assets', '/eld/v1/tracker-models', 'Tracker models that mark an asset ELD-enabled',
   'Optional. Not needed if Tenna filters server-side on assets?eld=true.',
   [q('eld', 'Only ELD models.', True, schema={'type': 'boolean'})], 'TrackerModel', True,
   [('ELD tracker models', {'eld': 'true'}, [{'model': 'WQ-ELD'}, {'model': 'WQ-ELD-2'}])]),
  ('T5', 'T5 Sites', '/eld/v1/sites', 'Yard sites with boundaries',
   'Called by the phone once a day and cached, because the yard-move check runs offline. Tenna Sites is the source.',
   [q('type', 'Site type.', 'yard', required=True)], 'Site', True,
   [('Yard sites', {'type': 'yard'}, [{'id': 'sit_77', 'name': 'Blue Ash Yard', 'type': 'yard',
      'geometry': {'type': 'Polygon', 'coordinates': [[[-84.5972, 39.2948], [-84.5951, 39.2948], [-84.5951, 39.2961], [-84.5972, 39.2961], [-84.5972, 39.2948]]]},
      'updated_at': '2026-09-02T15:10:00Z'}])]),
  ('T6', 'T6 Work orders', '/eld/v1/work-orders', 'Open work orders for an asset',
   'Called by the phone on D27 (shop road test stamp) and on D2 (job number pre-fill). The ELD never writes back. New surface.',
   [q('asset_id', 'The paired asset.', 'ast_2181', required=True), q('status', 'Work order status.', 'open')],
   'WorkOrder', True,
   [('Open work orders for asset', {'asset_id': 'ast_2181', 'status': 'open'},
     [{'id': 'wo_88213', 'number': 'WO-88213', 'job_number': 'J-2291', 'asset_id': 'ast_2181',
       'summary': 'Brake inspection', 'assigned_to': 'usr_5510'}])]),
  ('T7', 'T7 DVIR', '/eld/v1/dvir/status', "Today's inspection status for one asset",
   'Called when D14 opens. The ELD does not run inspections; it checks status and hands off. '
   'Launch link: tenna://dvir/new?asset_id=ast_2181&return=tennaeld://dvir/done. '
   "Tenna's app opens the return link when the inspection is saved.",
   [q('asset_id', 'The paired asset.', 'ast_2181', required=True)], 'DvirStatus', False,
   [('DVIR status', {'asset_id': 'ast_2181'}, {'status': 'submitted', 'inspection_id': 'insp_40917',
      'submitted_at': '2026-09-17T11:12:00Z', 'defects_open': 0, 'shipping_document_number': None})]),
  ('T8', 'T8 Entitlements', '/eld/v1/entitlements', 'ELD module and permissions for the caller',
   'Called by the phone at sign-in alongside T1, and by the micro-frontend when it mounts.',
   [], 'Entitlements', False,
   [('Get entitlements', {}, {'account_id': 'acc_0413', 'modules': {'eld': True},
      'permissions': ['eld.logs.read', 'eld.logs.propose_edit', 'eld.settings.write', 'eld.ud.assign', 'eld.transfer.request']})]),
]

INTRO = ("AppAxis's proposed contracts for what the Tenna ELD reads from the Tenna platform (Contract C, surfaces T1 to T8). "
         "Field names and paths are proposals, not Tenna's schema. Tenna maps each field to its real column or attribute and marks it "
         "exists, nullable or missing. Every call is a read. Every call sends the Cognito JWT and is scoped to the caller's account. "
         "No server implements this yet, so requests cannot be sent; the examples show the intended shapes. "
         "Source of truth: the Data contracts section of the architecture page.")

def openapi():
    paths = {}
    for surf, tag, path, summary, desc, params, ref, arr, reqs in OPS:
        item = {'$ref': f'#/components/schemas/{ref}'}
        schema = {'type': 'array', 'items': item} if arr else item
        examples = {name.lower().replace(' ', '_').replace('(', '').replace(')', ''): {'summary': name, 'value': body} for name, _, body in reqs}
        paths[path] = {'get': {
            'tags': [tag], 'summary': summary, 'description': desc,
            'operationId': 'get_' + path.split('/eld/v1/')[1].replace('/', '_').replace('-', '_'),
            'parameters': params,
            'responses': {
                '200': {'description': 'OK', 'content': {'application/json': {'schema': schema, 'examples': examples}}},
                '401': {'description': 'Missing, expired or invalid token', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}},
                '403': {'description': 'Account lacks the ELD module, or caller lacks the permission', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}},
            }}}
    tags = [{'name': 'T1 Identity', 'description': 'Not an endpoint. See the TokenClaims schema and the bearer security scheme.'}]
    seen = set()
    for _, tag, *_ in OPS:
        if tag not in seen: seen.add(tag); tags.append({'name': tag})
    return {
        'openapi': '3.0.3',
        'info': {'title': 'Tenna platform APIs read by the ELD (proposed)', 'version': VERSION, 'description': INTRO},
        'servers': [{'url': 'https://api.tenna.example', 'description': 'Placeholder. Tenna picks the real host and prefix.'}],
        'security': [{'cognitoJwt': []}],
        'tags': tags, 'paths': paths,
        'components': {
            'securitySchemes': {'cognitoJwt': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT',
                                'description': 'Cognito access token from the pool every Tenna app uses. Claims: see TokenClaims.'}},
            'schemas': SCHEMAS},
    }

def postman():
    folders, order = {}, []
    for surf, tag, path, summary, desc, params, ref, arr, reqs in OPS:
        if tag not in folders: folders[tag] = []; order.append(tag)
        for name, query, body in reqs:
            qs = [{'key': k, 'value': v} for k, v in query.items()]
            raw = '{{baseUrl}}' + path + ('?' + '&'.join(f'{k}={v}' for k, v in query.items()) if query else '')
            url = {'raw': raw, 'host': ['{{baseUrl}}'], 'path': path.strip('/').split('/')}
            if qs: url['query'] = qs
            request = {'method': 'GET', 'header': [{'key': 'Accept', 'value': 'application/json'}], 'url': url,
                       'description': f'{summary}.\n\n{desc}'}
            folders[tag].append({'name': name, 'request': request, 'response': [{
                'name': f'200 {name}', 'originalRequest': request, 'status': 'OK', 'code': 200,
                '_postman_previewlanguage': 'json', 'header': [{'key': 'Content-Type', 'value': 'application/json'}],
                'body': json.dumps(body, indent=2)}]})
    items = [{'name': 'T1 Identity (token claims)', 'description':
              'Not an endpoint. Every request sends the Cognito JWT as a bearer token. Claims the ELD relies on:\n\n```json\n'
              + json.dumps(SCHEMAS['TokenClaims']['example'], indent=2) + '\n```\n\nOpen: an `acting_as` claim for Tenna staff sessions.',
              'item': []}]
    items += [{'name': t, 'item': folders[t]} for t in order]
    return {
        'info': {'_postman_id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'appaxis-tenna-eld-contract-c')),
                 'name': 'Tenna ELD - proposed Tenna platform contracts (T1-T8)', 'description': INTRO + f'\n\nVersion {VERSION}.',
                 'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
        'auth': {'type': 'bearer', 'bearer': [{'key': 'token', 'value': '{{token}}', 'type': 'string'}]},
        'variable': [{'key': 'baseUrl', 'value': 'https://api.tenna.example'}, {'key': 'token', 'value': ''}],
        'item': items,
    }

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, doc in (('tenna-eld-contracts.openapi.json', openapi()), ('tenna-eld-contracts.postman_collection.json', postman())):
        with open(os.path.join(OUT, name), 'w') as f: json.dump(doc, f, indent=2); f.write('\n')
        print('wrote', name)
