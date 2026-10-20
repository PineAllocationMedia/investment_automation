#!/usr/bin/env python3
"""M1 daily research handoff. Offline intake, not a web scraper or rights grant.

init: create a blank 30-market research assignment (NO synthetic market prices).
assess: check all research decisions, prepare a fail-closed internal assessment,
        and emit a DRAFT-only M1 issue only with externally attested evidence.
Any reviewer references are human assertions to be independently authenticated.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from render_global_index_map import COUNTRIES, _dt, load_geometry, validate_map_issue
from render_macro_lens import InvalidIssue, payload_hash

HERE = Path(__file__).resolve().parent
CANDIDATES = HERE / 'examples' / 'm1_global_index_synthetic.json'
SCHEMA = 'M1_DAILY_RESEARCH_PACKET_V1'
SHA = re.compile(r'^[a-f0-9]{64}$')
STATES = {'UNRESEARCHED', 'EXCLUDED', 'QUALIFIED'}
EXCLUSIONS = {'MISSING', 'HOLIDAY', 'CLOSED', 'STALE', 'INCOMPARABLE'}


def require(ok, why):
    if not ok:
        raise InvalidIssue(why)


def url(value, label):
    require(isinstance(value, str) and value.startswith('https://'),
            label + ' requires original HTTPS evidence URL')
    host = urlparse(value).hostname or ''
    require(bool(host) and host not in ('example.org', 'example.com') and
            not host.endswith('.test') and not host.endswith('.invalid'),
            label + ' cannot be a placeholder')


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ' is required')
    return value.strip()


def scaffold(cutoff):
    d = _dt(cutoff, 'cutoff_utc')
    require(d.utcoffset().total_seconds() == 0, 'Cutoff must be UTC')
    template = json.loads(CANDIDATES.read_text(encoding='utf-8'))
    return {
        'schema_version': SCHEMA,
        'cutoff_utc': cutoff,
        'preparer_reference': None,
        'independent_auditor_reference': None,
        'rows': [
            {
                'selection_order': n,
                'economy_id': e['economy_id'],
                'economy_name': e['economy_name'],
                'index_candidate': e['instrument_name'],
                'currency_candidate': e['listed_currency'],
                'decision': 'UNRESEARCHED',
                'research_notes': None,
                'attempted_sources': [],
                'exclusion_status': None,
                'qualified_quote': None,
            }
            for n, e in enumerate(template['evidence'], 1)
        ],
        'notice': 'CANDIDATES ONLY; ZERO PRICES; NO SCAN PERFORMED; NO RIGHTS VERIFIED',
    }


def assess(packet, *, issue_metadata=None):
    require(isinstance(packet, dict) and packet.get('schema_version') == SCHEMA,
            'M1 research packet schema required')
    cutoff = _dt(packet.get('cutoff_utc'), 'cutoff_utc')
    require(cutoff.utcoffset().total_seconds() == 0, 'Cutoff must be UTC')
    rows = packet.get('rows')
    require(isinstance(rows, list) and len(rows) == 30, 'All 30 audit decisions required')
    require(isinstance(packet.get('preparer_reference'), (str, type(None))),
            'Preparer reference malformed')
    qualified, excluded, pending, reasons = {}, {}, [], []
    for n, row in enumerate(rows, 1):
        require(isinstance(row, dict), 'Row must be an object')
        code = COUNTRIES[n - 1]
        require(row.get('economy_id') == code and row.get('selection_order') == n,
                'Missing, swapped or duplicate candidate at row ' + str(n))
        state = row.get('decision')
        require(state in STATES, code + ' invalid decision')
        attempts = row.get('attempted_sources')
        require(isinstance(attempts, list), code + ' requires source attempt list')
        for attempt in attempts:
            url(attempt, code + ' attempted source')
        if state == 'UNRESEARCHED':
            require(row.get('qualified_quote') is None, code + ' cannot carry unreviewed quote')
            pending.append(code)
        elif state == 'EXCLUDED':
            require(row.get('qualified_quote') is None, code + ' excluded price must be null')
            require(row.get('exclusion_status') in EXCLUSIONS,
                    code + ' missing explicit exclusion status')
            reason = nonempty(row.get('research_notes'), code + ' exclusion reason')
            excluded[code] = (row['exclusion_status'], reason)
        else:
            q = row.get('qualified_quote')
            require(isinstance(q, dict), code + ' qualified quote required')
            require(row.get('exclusion_status') is None, code + ' conflicting exclusion')
            require(q.get('benchmark_variant') == 'PRICE_INDEX',
                    code + ' requires domestic price-index variant')
            require(q.get('return_currency') == 'LOCAL',
                    code + ' requires local return currency')
            require(q.get('currency') == row['currency_candidate'],
                    code + ' currency differs from configured candidate: manual registry review required')
            for key in ('index_name', 'publisher', 'source_title', 'capture_reference',
                        'benchmark_definition', 'rights_review_reference',
                        'independent_fact_review_reference'):
                nonempty(q.get(key), code + '.' + key)
            for key in ('original_price_source_url', 'rights_evidence_url'):
                url(q.get(key), code + '.' + key)
            capture = q.get('source_capture_sha256')
            require(isinstance(capture, str) and SHA.fullmatch(capture),
                    code + ' requires immutable original-source capture hash')
            require(q.get('rights_scope') == 'PUBLIC_BLOSSOM_INDEX_RETURN_GRAPHIC',
                    code + ' exact intended usage rights scope not reviewed')
            require(q.get('rights_decision') == 'APPROVED_FOR_EXACT_USE',
                    code + ' data-use clearance not established')
            require(q.get('fact_decision') == 'INDEPENDENTLY_CHECKED',
                    code + ' independent original-source arithmetic review missing')
            require(q['independent_fact_review_reference'] != packet.get('preparer_reference'),
                    code + ' cannot independently review own facts')
            require(q['rights_review_reference'] != packet.get('preparer_reference'),
                    code + ' must have separate rights review')
            for key in ('prior_close', 'current_close'):
                v = q.get(key)
                require(type(v) in (int, float) and math.isfinite(v) and v > 0,
                        code + ' invalid index close')
            prior = _dt(q.get('prior_observed_at'), code + '.prior_observed_at')
            current = _dt(q.get('observed_at'), code + '.observed_at')
            retrieved = _dt(q.get('retrieved_at'), code + '.retrieved_at')
            require(prior < current <= retrieved <= cutoff,
                    code + ' invalid completed close/observation/retrieval cutoff')
            require(q.get('session_status') == 'COMPLETED',
                    code + ' provisional session cannot appear on a daily map')
            # Capture SHA and reviewer references are *claims*; a separate audit
            # must access the actual capture, original source and rights grant.
            qualified[code] = q
    ready = not pending and len(qualified) >= 4 and bool(
        packet.get('independent_auditor_reference')) and bool(
        packet.get('preparer_reference'))
    if pending:
        reasons.append(str(len(pending)) + ' country research decisions still UNRESEARCHED')
    if len(qualified) < 4:
        reasons.append('At least four independently qualified countries required')
    if not packet.get('independent_auditor_reference'):
        reasons.append('Independent complete-packet auditor reference absent')
    if not packet.get('preparer_reference'):
        reasons.append('Research preparer reference absent')
    require(packet.get('independent_auditor_reference') != packet.get('preparer_reference')
            or not ready, 'Research preparer cannot be independent auditor')
    report = {
        'status': 'CANDIDATE_READY_REQUIRES_EXTERNAL_AUDIT' if ready else 'HOLD',
        'count_selected': len(rows), 'count_qualified': len(qualified),
        'count_excluded': len(excluded), 'count_unresearched': len(pending),
        'displayed_market_codes': list(qualified),
        'excluded_market_codes': list(excluded),
        'unresearched_market_codes': pending,
        'blockers': reasons,
        'packet_sha256': payload_hash(packet),
        'rights_and_source_truth': 'HUMAN_ASSERTIONS_ONLY_NOT_INDEPENDENTLY_VERIFIED_BY_CODE',
    }
    if not ready or issue_metadata is None:
        return report, None
    issue = issue_from_evidence(packet, qualified, excluded, issue_metadata)
    validate_map_issue(issue, load_geometry())
    return report, issue


def issue_from_evidence(packet, qualified, excluded, meta):
    # This is intentionally never a RELEASE. The exact issue/caption/images and
    # source captures still require a distinct independent audit and CEO approval.
    require(isinstance(meta, dict), 'M1 issue metadata object required')
    sample = json.loads(CANDIDATES.read_text(encoding='utf-8'))
    for key in ('issue_id', 'headline', 'deck', 'interpretation', 'caption'):
        sample[key] = nonempty(meta.get(key), key)
    sample.update({
        'cutoff_utc': packet['cutoff_utc'],
        'rights_note': 'REVIEWED_FOR_EXACT_USE',
        'universe_review': 'COVERAGE_VALIDATED',
        'benchmark_registry_status': 'INDEPENDENTLY_VERIFIED',
        'scan_status': 'COMPLETE_AUDITED',
        'method_version': 'M1_INDEX_LOCAL_PRICE_V0.4',
        'universe_version': 'CEO_SELECTED_30_COUNTRIES_RESEARCH_V1',
    })
    for row in sample['evidence']:
        code = row['economy_id']
        row['verification'] = 'VERIFIED'
        row['original_price_source_url'] = None
        row['close_price'] = row['prior_close_price'] = row['signed_return_pct'] = None
        row['close_session_date'] = row['prior_session_date'] = None
        row['observed_at'] = row['prior_observed_at'] = row['retrieved_at'] = None
        row['source_title'] = 'NO QUALIFIED ORIGINAL CLOSE'
        row['verification_note'] = 'INTERNAL AUDIT REGISTER; REVIEW SOURCE CAPTURES'
        row['rights_note'] = 'NOT APPROVED FOR DISPLAY'
        row['session_status'] = 'UNVERIFIED'
        row['missing_status'] = 'MISSING'
        row['benchmark_variant'] = 'UNCONFIRMED'
        if code in excluded:
            row['missing_status'], reason = excluded[code]
            row['verification_note'] = reason[:160]
        elif code in qualified:
            q = qualified[code]
            row.update({
                'instrument_kind': 'INDEX',
                'instrument_name': q['index_name'],
                'instrument_provider': q['publisher'],
                'benchmark_definition': q['benchmark_definition'],
                'benchmark_variant': 'PRICE_INDEX',
                'return_currency': 'LOCAL',
                'listed_currency': q['currency'],
                'session_status': 'COMPLETED',
                'missing_status': 'ELIGIBLE',
                'prior_close_price': q['prior_close'],
                'close_price': q['current_close'],
                'signed_return_pct': (q['current_close'] / q['prior_close'] - 1) * 100,
                'prior_observed_at': q['prior_observed_at'],
                'observed_at': q['observed_at'],
                'retrieved_at': q['retrieved_at'],
                'prior_session_date': _dt(q['prior_observed_at'], 'prior').date().isoformat(),
                'close_session_date': _dt(q['observed_at'], 'current').date().isoformat(),
                'original_price_source_url': q['original_price_source_url'],
                'source_title': q['source_title'],
                'rights_note': ('RIGHTS REVIEW ' + q['rights_review_reference'])[:160],
                'verification_note': ('INDEPENDENT FACT REVIEW ' +
                                      q['independent_fact_review_reference'])[:160],
            })
    return sample


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    a = sub.add_parser('init')
    a.add_argument('--cutoff-utc', required=True)
    a.add_argument('--out', type=Path, required=True)
    b = sub.add_parser('assess')
    b.add_argument('packet', type=Path)
    b.add_argument('--report', type=Path, required=True)
    b.add_argument('--issue-metadata', type=Path)
    b.add_argument('--draft-issue', type=Path)
    args = ap.parse_args(argv)
    try:
        if args.command == 'init':
            obj = scaffold(args.cutoff_utc)
            args.out.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            print('CREATED UNRESEARCHED 30-market intake; NOT A MARKET SCAN')
            return 0
        packet = json.loads(args.packet.read_text(encoding='utf-8'))
        metadata = (json.loads(args.issue_metadata.read_text(encoding='utf-8'))
                    if args.issue_metadata else None)
        require(not args.draft_issue or metadata is not None,
                'A candidate M1 draft requires approved editorial issue metadata')
        report, issue = assess(packet, issue_metadata=metadata)
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if issue and args.draft_issue:
            args.draft_issue.write_text(json.dumps(issue, indent=2) + '\n',
                                        encoding='utf-8')
        print(report['status'], report['count_qualified'], '/ 30')
        return 0 if issue is not None else 2
    except (InvalidIssue, OSError, KeyError, TypeError, ValueError) as exc:
        print('HOLD:', exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
