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
ETF_TEMPLATE = HERE / 'examples' / 'm1_us_etf_synthetic.json'
ETF_RESEARCH_MODE = 'US_LISTED_ETF_USD'
LOCAL_RESEARCH_MODE = 'LOCAL_DOMESTIC_INDEX'
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


def verified_local_capture(root, relative, expected_sha, label):
    # Local evidence integrity, not proof that its contents are an authentic
    # source or that third-party redistribution has been authorized.
    require(root is not None, label + ' requires a local evidence-root directory')
    require(isinstance(relative, str) and relative.strip(), label + ' capture path required')
    require(isinstance(expected_sha, str) and SHA.fullmatch(expected_sha),
            label + ' capture SHA-256 required')
    root = Path(root).resolve()
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts,
            label + ' capture path cannot escape evidence root')
    absolute = (root / path).resolve()
    require(absolute.is_relative_to(root) and absolute.is_file(),
            label + ' local capture missing or outside evidence root')
    require(0 < absolute.stat().st_size <= 16 * 1024 * 1024,
            label + ' capture must be nonempty and <=16 MiB')
    actual = hashlib.sha256(absolute.read_bytes()).hexdigest()
    require(actual == expected_sha, label + ' capture contents mismatch recorded hash')


def scaffold(cutoff, *, research_mode=LOCAL_RESEARCH_MODE):
    d = _dt(cutoff, 'cutoff_utc')
    require(d.utcoffset().total_seconds() == 0, 'Cutoff must be UTC')
    require(research_mode in (LOCAL_RESEARCH_MODE, ETF_RESEARCH_MODE),
            'Unknown M1 research mode')
    template_file = ETF_TEMPLATE if research_mode == ETF_RESEARCH_MODE else CANDIDATES
    template = json.loads(template_file.read_text(encoding='utf-8'))
    return {
        'research_mode': research_mode,
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
                'etf_ticker_candidate': e.get('etf_ticker') if
                    research_mode == ETF_RESEARCH_MODE else None,
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


def assess(packet, *, issue_metadata=None, evidence_root=None):
    require(isinstance(packet, dict) and packet.get('schema_version') == SCHEMA,
            'M1 research packet schema required')
    mode=packet.get('research_mode', LOCAL_RESEARCH_MODE)
    require(mode in (LOCAL_RESEARCH_MODE, ETF_RESEARCH_MODE),
            'Unsupported research mode: no mixed index/ETF dataset')
    etf_mode=mode==ETF_RESEARCH_MODE
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
        if etf_mode:
            from m1_country_etf_mode import ETF_CANDIDATES
            candidate=ETF_CANDIDATES.get(code)
            require(row.get('etf_ticker_candidate')==
                    (candidate['ticker'] if candidate else None),
                    code + ' candidate fund registry substituted')
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
            require(q.get('benchmark_variant') ==
                    ('ETF_EXCHANGE_PRICE' if etf_mode else 'PRICE_INDEX'),
                    code + ' wrong instrument price basis')
            require(q.get('return_currency') == ('USD' if etf_mode else 'LOCAL'),
                    code + ' wrong quote currency/return basis')
            if etf_mode:
                require(candidate is not None and q.get('etf_ticker')==
                        candidate['ticker'] and q.get('index_name')==candidate['name'],
                        code + ' no confirmed active single-country ETF mapping')
                require(q.get('etf_price_basis')=='UNADJUSTED_US_EXCHANGE_CLOSE',
                        code + ' ETF NAV/adjusted return cannot substitute for exchange close')
                require(q.get('corporate_action_review')==
                        'NO_MATERIAL_SPLIT_OR_EX_DISTRIBUTION',
                        code + ' split/distribution event unresolved')
                require(q.get('proxy_scope')=='SINGLE_COUNTRY_UNHEDGED',
                        code + ' fund is not an unhedged single-country exposure')
            require(q.get('currency') == row['currency_candidate'],
                    code + ' currency differs from configured candidate: manual registry review required')
            for key in ('index_name', 'publisher', 'source_title', 'capture_reference',
                        'benchmark_definition', 'rights_review_reference',
                        'independent_fact_review_reference'):
                nonempty(q.get(key), code + '.' + key)
            for key in ('original_price_source_url', 'rights_evidence_url'):
                url(q.get(key), code + '.' + key)
            verified_local_capture(evidence_root, q.get('source_capture_path'),
                                   q.get('source_capture_sha256'),
                                   code + ' original-source')
            verified_local_capture(evidence_root, q.get('rights_capture_path'),
                                   q.get('rights_capture_sha256'),
                                   code + ' rights-evidence')
            require(q.get('rights_scope') ==
                    ('PUBLIC_BLOSSOM_ETF_USD_GRAPHIC' if etf_mode else
                     'PUBLIC_BLOSSOM_INDEX_RETURN_GRAPHIC'),
                    code + ' exact intended data rights scope not reviewed')
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
            if etf_mode:
                prior_session=prior.date().isoformat()
                close_session=current.date().isoformat()
                require(q.get('close_session_date')==close_session and
                        q.get('prior_session_date')==prior_session and
                        prior.hour==16 and current.hour==16 and
                        prior.utcoffset().total_seconds() in (-18000,-14400) and
                        current.utcoffset().total_seconds() in (-18000,-14400),
                        code + ' requires completed matching 16:00 ET US session')
                if qualified:
                    first=next(iter(qualified.values()))
                    require((q['close_session_date'],q['prior_session_date'])==
                            (first['close_session_date'],first['prior_session_date']),
                            code + ' incompatible US ETF session dates')
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
        'research_mode': mode,
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
    etf_mode=packet.get('research_mode')==ETF_RESEARCH_MODE
    sample=json.loads((ETF_TEMPLATE if etf_mode else CANDIDATES)
                      .read_text(encoding='utf-8'))
    for key in ('issue_id', 'headline', 'deck', 'interpretation', 'caption'):
        sample[key] = nonempty(meta.get(key), key)
    sample.update({
        'cutoff_utc': packet['cutoff_utc'],
        'rights_note': 'REVIEWED_FOR_EXACT_USE',
        'universe_review': 'COVERAGE_VALIDATED',
        'benchmark_registry_status': 'INDEPENDENTLY_VERIFIED',
        'scan_status': 'COMPLETE_AUDITED',
        'method_version': 'M1_ETF_USD_PRICE_V0.1' if etf_mode else
                          'M1_INDEX_LOCAL_PRICE_V0.4',
        'universe_version': 'CEO_30_COUNTRIES_US_ETF_PROXY_V1' if etf_mode else
                            'CEO_SELECTED_30_COUNTRIES_RESEARCH_V1',
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
        row['benchmark_variant'] = ('NO_PROXY' if etf_mode and row['etf_ticker'] is None
                                    else 'ETF_EXCHANGE_PRICE' if etf_mode else 'UNCONFIRMED')
        if code in excluded:
            row['missing_status'], reason = excluded[code]
            row['verification_note'] = reason[:160]
        elif code in qualified:
            q = qualified[code]
            row.update({
                'instrument_kind': 'ETF' if etf_mode else 'INDEX',
                'instrument_name': q['index_name'],
                'instrument_provider': q['publisher'],
                'benchmark_definition': q['benchmark_definition'],
                'benchmark_variant': 'ETF_EXCHANGE_PRICE' if etf_mode else 'PRICE_INDEX',
                'return_currency': 'USD' if etf_mode else 'LOCAL',
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
                **({'etf_ticker':q['etf_ticker'],
                    'etf_price_basis':q['etf_price_basis'],
                    'corporate_action_review':q['corporate_action_review']}
                   if etf_mode else {}),
            })
    return sample


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    a = sub.add_parser('init')
    a.add_argument('--cutoff-utc', required=True)
    a.add_argument('--mode', choices=('index','usd-etf'), default='index')
    a.add_argument('--out', type=Path, required=True)
    b = sub.add_parser('assess')
    b.add_argument('packet', type=Path)
    b.add_argument('--report', type=Path, required=True)
    b.add_argument('--issue-metadata', type=Path)
    b.add_argument('--draft-issue', type=Path)
    b.add_argument('--evidence-root', type=Path)
    args = ap.parse_args(argv)
    try:
        if args.command == 'init':
            obj = scaffold(args.cutoff_utc, research_mode=(ETF_RESEARCH_MODE if
                           args.mode=='usd-etf' else LOCAL_RESEARCH_MODE))
            args.out.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            print('CREATED UNRESEARCHED 30-market intake; NOT A MARKET SCAN')
            return 0
        packet = json.loads(args.packet.read_text(encoding='utf-8'))
        metadata = (json.loads(args.issue_metadata.read_text(encoding='utf-8'))
                    if args.issue_metadata else None)
        require(not args.draft_issue or metadata is not None,
                'A candidate M1 draft requires approved editorial issue metadata')
        report, issue = assess(packet, issue_metadata=metadata,
                               evidence_root=args.evidence_root)
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
