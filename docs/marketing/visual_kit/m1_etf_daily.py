#!/usr/bin/env python3
"""PAM MARKET ATLAS: authentic ETF close facts -> exact clean image -> Prompt 3 QA.

No market scraping, paid feed, permissions assertion or automatic publication.
Researchers supply US ETF closing prices and public attribution URLs in one CSV.
The strict legacy evidence-intake path remains available for specialist work.
"""
import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from m1_country_etf_mode import ETF_CANDIDATES, ETF_COUNTRIES, NO_ETF_PROXY
from render_global_index_map import (
    COUNTRIES, APPROVED_LOGO_SHA256, load_geometry, render_global_map,
    validate_map_issue,
)
from render_macro_lens import checked_logo, payload_hash, need, InvalidIssue

HERE=Path(__file__).resolve().parent
SAMPLE=HERE/'examples'/'m1_us_etf_synthetic.json'
US_TZ=ZoneInfo('America/New_York')
MARKET_ATLAS_HEADLINE='The world in one U.S. session'
COLUMNS=['country','ticker','prior_close','close','source_url',
         'prior_source_url','source_name','corporate_action_status',
         'source_use_status','notes']
PLACEHOLDER_DOMAINS={'example.com','example.org','example.net','localhost'}


def url(value, field):
    need(isinstance(value,str) and value.startswith('https://'),
         field+' requires genuine HTTPS source URL')
    parsed=urlparse(value)
    host=(parsed.hostname or '').lower()
    need(bool(host) and host not in PLACEHOLDER_DOMAINS and
         not host.endswith('.example') and not parsed.username,
         field+' cannot contain fictitious sources or credentials')
    return value


def init_csv(path):
    with Path(path).open('w',newline='',encoding='utf-8') as fp:
        writer=csv.DictWriter(fp,fieldnames=COLUMNS)
        writer.writeheader()
        for code in ETF_COUNTRIES:
            ticker=ETF_CANDIDATES.get(code,{}).get('ticker','')
            writer.writerow({'country':code,'ticker':ticker})
    return len(ETF_COUNTRIES)


def records(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as fp:
        reader=csv.DictReader(fp)
        need(reader.fieldnames is not None and
             set(COLUMNS).issubset(set(reader.fieldnames)),
             'M1 CSV needs columns: '+', '.join(COLUMNS))
        rows=list(reader)
    need(len(rows) in (len(COUNTRIES),len(ETF_COUNTRIES)),
         'M1 CSV requires original 30 countries or expanded 33 countries')
    selected=ETF_COUNTRIES if len(rows)==len(ETF_COUNTRIES) else COUNTRIES
    for i,(row,code) in enumerate(zip(rows,selected),1):
        need(row['country'].strip()==code,
             f'M1 CSV country row {i} must be {code} in canonical order')
        ticker=ETF_CANDIDATES.get(code,{}).get('ticker','')
        need(row['ticker'].strip()==ticker,
             f'{code}: ticker must match the reviewed country-ETF registry')
    return rows


def et_close(day):
    return datetime.combine(day,time(16,0),tzinfo=US_TZ)


def race_recap_caption(eligible,session_date,prior_date):
    """Natural, verifiable leaderboard framing based ONLY on price-pair facts.

    This is editorial copy, not an assertion that a particular country's
    domestic index, currency, economy or underlying equities all moved alike.
    """
    need(len(eligible)>=1,'A factual Market Atlas recap requires at least one real return')
    ranked=sorted(eligible,key=lambda e:(-e['signed_return_pct'],e['economy_id']))
    leader,tail=ranked[0],ranked[-1]
    # Last in descending order is the weakest return. Ties are factual
    # co-leaders; avoid implying an arbitrary alphabetical winner is unique.
    top=leader['signed_return_pct'];bottom=tail['signed_return_pct']
    spread=top-bottom
    gainers=sum(e['signed_return_pct']>0 for e in eligible)
    decliners=sum(e['signed_return_pct']<0 for e in eligible)
    flats=len(eligible)-gainers-decliners
    if len(eligible)==1:
        hook="One country ETF at the closing bell."
    elif spread<0.005:
        hook="A dead heat on the country ETF board."
    elif gainers==0 and flats==0:
        hook="Everyone finished in the red. Some fell a lot harder."
    elif decliners==0 and flats==0:
        hook="All green on the ETF board. Not everyone kept pace."
    elif spread>=3:
        hook=f"One closing bell. {spread:.2f} percentage points between first and last."
    else:
        hook="One U.S. session. Very different finishes."
    if len(eligible)==1:
        ordering=(f"{leader['economy_name']} ({leader['etf_ticker']}) "
                  f"finished at {top:+.2f}%.")
    elif spread<0.005:
        ordering=(f"All {len(eligible)} plotted country ETFs closed essentially level "
                  f"at {top:+.2f}%.")
    else:
        ordering=(f"{leader['economy_name']} ({leader['etf_ticker']}) led the board "
                  f"at {top:+.2f}%; {tail['economy_name']} ({tail['etf_ticker']}) "
                  f"brought up the rear at {bottom:+.2f}%.")
    score=f"{gainers} higher, {decliners} lower"
    if flats: score+=f", {flats} unchanged"
    score+=f" across {len(eligible)} plotted ETFs."
    # Distinguish factual results and any suggested causal narrative.
    caveat=("These are USD prices of U.S.-listed country ETFs, not domestic "
            "stock-index returns. FX and U.S.-hours repricing matter.")
    sourced=sorted({e['source_title'] for e in eligible})
    sources=("Source: "+sourced[0]+"." if len(sourced)==1 else
             "Price-source links retained in the evidence register.")
    caption=(f"{hook} {ordering} {score} {caveat} "
             f"U.S. session: {session_date} vs {prior_date}. {sources}")
    need(len(caption)<=1200,'M1 generated caption too long')
    return caption


def build(quotes,session_date,prior_date,cutoff_utc,*,issue_id,headline=None,logo=None):
    current=date.fromisoformat(session_date)
    prior=date.fromisoformat(prior_date)
    cutoff=datetime.fromisoformat(cutoff_utc.replace('Z','+00:00'))
    need(cutoff.tzinfo is not None and cutoff.utcoffset()==timedelta(0),
         'Cutoff must be ISO UTC with Z or +00:00')
    need(0<(current-prior).days<=7 and current.weekday()<5 and
         prior.weekday()<5,'Use consecutive actual completed US trading dates, not weekends')
    close_et=et_close(current)
    earlier_et=et_close(prior)
    need(close_et.astimezone(timezone.utc)<=cutoff,
         'Today\'s US market has not yet closed; use the last completed session')
    need((cutoff-close_et.astimezone(timezone.utc))<=timedelta(hours=96),
         'Too old for daily briefing: choose a recent completed session')
    source_rows=records(quotes)
    template=json.loads(SAMPLE.read_text(encoding='utf-8'))
    p=template
    p.update({
        'issue_id':issue_id,
        'cutoff_utc':cutoff.isoformat().replace('+00:00','Z'),
        'rights_note':'RESEARCH_PREVIEW',
        'scan_status':'RESEARCH_PREVIEW',
        'universe_review':'RESEARCH_COVERAGE',
        'benchmark_registry_status':'SOURCE_LINKED_RESEARCH',
        'method_version':'M1_ETF_USD_DAILY_V1',
        'map_product':'MARKET_ATLAS_V1',
        # Title/composition stay invariant across sessions. A requested
        # alternative hook belongs in the caption, not on the fixed map.
        'headline':MARKET_ATLAS_HEADLINE,
        'deck':f'Country ETF moves in USD / US close {current.isoformat()} vs {prior.isoformat()}',
        'interpretation':'USD ETF returns reflect currency and US trading-hours repricing, not domestic index returns.',
        'caption':'PENDING PRICE-BASED EDITORIAL RECAP',
        'session_date':current.isoformat(),
        'prior_session_date':prior.isoformat(),
    })
    if len(source_rows)==len(ETF_COUNTRIES):
        # Leave the validated legacy 30-country example unchanged. The expanded
        # daily ETF product appends three optional price observations in order.
        # All values are reset to MISSING below unless real close pairs exist.
        for code,name in (('ARG','Argentina'),('CHL','Chile'),('THA','Thailand')):
            candidate=ETF_CANDIDATES[code]
            row=p['evidence'][0].copy()
            row.update(economy_id=code,geometry_id=code,economy_name=name,
                       instrument_name=candidate['name'],
                       instrument_provider=candidate['issuer'],
                       issuer_product_url=candidate['issuer_url'],
                       etf_ticker=candidate['ticker'],
                       selection_order=len(p['evidence'])+1)
            if code=='ARG':
                row['country_exposure_note']=(
                    'Argentina-focused index includes offshore/ADR company exposures')
            p['evidence'].append(row)
        p['selection_basis']='CEO_SELECTED_33_COUNTRIES'
        p['universe_version']='CEO_33_COUNTRIES_US_ETF_PROXY_V2'
    if logo is not None:
        raw=checked_logo(logo)
        need(hashlib.sha256(raw).hexdigest()==APPROVED_LOGO_SHA256,
             'Exact CEO-approved pine master required')
        p['brand_logo_sha256']=APPROVED_LOGO_SHA256
    displayed=[];omitted=[]
    for r,e in zip(source_rows,p['evidence']):
        code=e['economy_id']; ticker=e.get('etf_ticker')
        a=(r.get('prior_close') or '').strip()
        b=(r.get('close') or '').strip()
        src=(r.get('source_url') or '').strip()
        prev_src=(r.get('prior_source_url') or '').strip() or src
        source_name=(r.get('source_name') or '').strip()
        action=(r.get('corporate_action_status') or '').strip().upper()
        use=(r.get('source_use_status') or '').strip().upper()
        e.update(verification='SOURCE_LINKED_PREVIEW',
                 rights_note='PUBLIC FACT RESEARCH / PROMPT 3 REVIEW PENDING',
                 verification_note='UNREVIEWED SOURCE FACTS / PROMPT 3 PENDING',
                 source_title='NO OBSERVATION QUALIFIED',
                 session_status='UNVERIFIED',
                 missing_status='MISSING',
                 close_price=None,prior_close_price=None,signed_return_pct=None,
                 observed_at=None,prior_observed_at=None,retrieved_at=None,
                 close_session_date=None,prior_session_date=None,
                 original_price_source_url=None,
                 corporate_action_review=None)
        if not ticker:
            need(not any((a,b,src,prev_src,r.get('ticker',''))),
                 code+' no active approved US single-country ETF')
            omitted.append(code)
            continue
        if not any((a,b,src,source_name,action,use)):
            omitted.append(code)
            continue
        need(bool(a)==bool(b),code+' prior/current close must both be present')
        need(bool(a) and bool(src) and bool(source_name),
             code+' source URL/name and both prices are required')
        try:
            av=float(a);bv=float(b)
        except ValueError as err:
            raise InvalidIssue(code+' prices must be numeric') from err
        need(math.isfinite(av) and math.isfinite(bv) and av>0 and bv>0,
             code+' invalid ETF market closing price')
        move=(bv/av-1)*100
        need(abs(move)<=20,code+' extraordinary daily move requires human review')
        url(src,code+'.source_url');url(prev_src,code+'.prior_source_url')
        need(len(source_name)<=50,code+' source name must be <=50 chars')
        need(action in ('CHECKED_CLEAR','NO_KNOWN_EVENT'),
             code+' split/ex-distribution issue unresolved: omit until reviewed')
        need(use in ('NO_KNOWN_RESTRICTION','REVIEW_PENDING'),
             code+' known-restricted source must not be used')
        e.update(
            close_price=bv,prior_close_price=av,signed_return_pct=move,
            session_status='COMPLETED',missing_status='ELIGIBLE',
            observed_at=close_et.isoformat(),
            prior_observed_at=earlier_et.isoformat(),
            retrieved_at=cutoff.isoformat(),
            close_session_date=current.isoformat(),
            prior_session_date=prior.isoformat(),
            original_price_source_url=src,
            prior_price_source_url=prev_src,
            price_source_title=source_name,
            source_title=source_name,
            corporate_action_review=('NO_MATERIAL_SPLIT_OR_EX_DISTRIBUTION'
                                      if action=='CHECKED_CLEAR'
                                      else 'NO_KNOWN_MATERIAL_ACTION'),
            source_use_status=use,
            rights_note='PUBLIC CLOSING PRICE / SOURCE LINKED',
            verification_note='SOURCE-LINKED REAL FACT; PROMPT 3 UNCHECKED',
        )
        displayed.append(code)
    need(len(displayed)>=1,
         'At least one genuine source-linked close pair is necessary; search further before giving up')
    eligible=[e for e in p['evidence'] if e['missing_status']=='ELIGIBLE']
    p['caption']=race_recap_caption(eligible,current.isoformat(),prior.isoformat())
    p['caption_review_state']='DRAFT_AWAITING_PROMPT3'
    validate_map_issue(p,load_geometry())
    return p,{'state':'DRAFT_REAL_DATA_AWAITING_PROMPT3','displayed':displayed,
              'omitted':omitted,'count_shown':len(displayed),
              'session_date':session_date,'prior_session_date':prior_date,
              'source_use_clearance':'NOT_IMPLIED_BY_SOURCE_LINKS',
              'caption_draft':p['caption']}


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def exact_asset_manifest(issue,quote_csv,svg_path,svg,png_path,png,mobile_path,mobile):
    """Immutable file-byte handoff for Prompt 3. Still NOT publication approval."""
    need(issue.get('artifact_intent')=='EXACT_ARTIFACT_AWAITING_PROMPT3',
         'Only approved-brand exact-image candidate can generate this manifest')
    need(png is not None and mobile is not None,
         'Exact-image handoff requires native and 390px preview bytes')
    return {
        'schema':'M1_EXACT_ASSET_HANDOFF_V1',
        'state':'PENDING_INDEPENDENT_AUDIT_AND_CEO_APPROVAL',
        'issue_sha256':payload_hash(issue),
        'caption_sha256':_sha(issue['caption'].encode('utf-8')),
        'quote_csv_sha256':_sha(Path(quote_csv).read_bytes()),
        'brand_logo_sha256':issue['brand_logo_sha256'],
        'assets':{
            'svg':{'path':str(svg_path.resolve()),'sha256':_sha(svg.encode('utf-8'))},
            'png':{'path':str(png_path.resolve()),'sha256':_sha(png)},
            'mobile_png':{'path':str(mobile_path.resolve()),'sha256':_sha(mobile)},
        },
        'publication_approved':False,
    }


def check_exact_manifest(issue,manifest):
    need(isinstance(manifest,dict) and
         manifest.get('schema')=='M1_EXACT_ASSET_HANDOFF_V1' and
         manifest.get('publication_approved') is False and
         manifest.get('state')=='PENDING_INDEPENDENT_AUDIT_AND_CEO_APPROVAL',
         'Exact-image manifest cannot authorize publication')
    need(manifest.get('issue_sha256')==payload_hash(issue),
         'Exact image manifest issue SHA mismatch')
    need(manifest.get('caption_sha256')==_sha(issue['caption'].encode('utf-8')),
         'Exact caption SHA mismatch')
    need(issue.get('artifact_intent')=='EXACT_ARTIFACT_AWAITING_PROMPT3',
         'Exact-image review requires the final-looking source-linked issue')
    need(manifest.get('brand_logo_sha256')==APPROVED_LOGO_SHA256 and
         issue.get('brand_logo_sha256')==APPROVED_LOGO_SHA256,
         'Exact-image manifest requires CEO-approved pine-logo identity')
    assets=manifest.get('assets',{})
    need(isinstance(assets,dict),'Exact-image asset hashes missing')
    for kind in ('svg','png','mobile_png'):
        entry=assets.get(kind)
        need(isinstance(entry,dict) and isinstance(entry.get('path'),str) and
             isinstance(entry.get('sha256'),str),
             'Exact image source/hash absent for '+kind)
        need(_sha(Path(entry['path']).read_bytes())==entry['sha256'],
             'Audited '+kind+' image differs from original Prompt 2 output')
    return assets


def review(preview,qa,manifest=None):
    """Check actual Prompt 3 claims against exact Prompt 2 pixels and caption.

    Never re-render at this stage. The CEO still separately approves publishing.
    """
    need(preview.get('rights_note')=='RESEARCH_PREVIEW',
         'Only a source-linked M1 research draft can enter this workflow')
    need(qa.get('issue_sha256')==payload_hash(preview),
         'Prompt 3 review does not match exact issue input hash')
    if preview.get('artifact_intent')=='EXACT_ARTIFACT_AWAITING_PROMPT3':
        need(manifest is not None,
             'Prompt 3 must audit the exact native/mobile image manifest')
        assets=check_exact_manifest(preview,manifest)
        for qa_key,asset in (('png_sha256','png'),
                             ('mobile_png_sha256','mobile_png'),
                             ('svg_sha256','svg')):
            need(qa.get(qa_key)==assets[asset]['sha256'],
                 'Prompt 3 did not audit exact '+asset+' bytes')
        need(qa.get('caption_sha256')==manifest['caption_sha256'],
             'Prompt 3 did not audit exact caption text')
    need(qa.get('fact_verdict')=='PASS' and
         qa.get('corporate_actions_verdict')=='PASS' and
         qa.get('source_use_verdict')=='NO_KNOWN_RESTRICTION' and
         qa.get('visual_verdict')=='PASS',
         'Prompt 3 has not cleared numbers, corporate actions, source terms and exact visual')
    for field in ('auditor_reference','source_use_review_reference'):
        need(isinstance(qa.get(field),str) and len(qa[field].strip())>=6,
             'Actual independent review reference required: '+field)
    need(qa['auditor_reference']!=qa['source_use_review_reference'] or
         qa.get('combined_reviewer_disclosure') is True,
         'Combined reviewer must be explicitly disclosed')
    p=json.loads(json.dumps(preview))
    p.update(rights_note='PUBLIC_FACTS_QA_PASSED',
             scan_status='COMPLETE_AUDITED',
             universe_review='COVERAGE_VALIDATED',
             benchmark_registry_status='INDEPENDENTLY_VERIFIED',
             fact_audit_reference=qa['auditor_reference'],
             source_use_review_reference=qa['source_use_review_reference'],
             publication_source_use_state='NO_KNOWN_RESTRICTION')
    for e in p['evidence']:
        e['verification']='VERIFIED'
        if e['missing_status']=='ELIGIBLE':
            e['corporate_action_review']='NO_MATERIAL_SPLIT_OR_EX_DISTRIBUTION'
            e['source_use_status']='NO_KNOWN_RESTRICTION'
            e['verification_note']='PROMPT 3 FACTS/CORPORATE ACTIONS REVIEWED'
    validate_map_issue(p,load_geometry())
    return p


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    a=sub.add_parser('init',help='Write the expanded 33-country ETF quote CSV for web research')
    a.add_argument('--out',type=Path,required=True)
    b=sub.add_parser('build',help='Create clean, consistent Market Atlas image from genuine completed-session ETF prices')
    b.add_argument('quotes',type=Path)
    for key in ('session-date','prior-date','cutoff-utc','issue-id'):
        b.add_argument('--'+key,required=True)
    b.add_argument('--headline')
    b.add_argument('--brand-logo',type=Path)
    b.add_argument('--out-issue',type=Path,required=True)
    b.add_argument('--svg',type=Path,required=True)
    b.add_argument('--png',type=Path)
    b.add_argument('--mobile-png',type=Path)
    b.add_argument('--asset-manifest',type=Path,
                   help='Required for exact candidate: SHA-256 of same PNG, SVG, mobile and caption')
    b.add_argument('--draft-only',action='store_true',
                   help='Optional legacy watermarked research proof; never publish')
    c=sub.add_parser('review',help='Check Prompt 3 QA against the EXACT original image and caption')
    c.add_argument('issue',type=Path)
    c.add_argument('--qa',type=Path,required=True)
    c.add_argument('--out-issue',type=Path,required=True)
    c.add_argument('--asset-manifest',type=Path,
                   help='Mandatory for clean Prompt 2 candidate review')
    args=ap.parse_args(argv)
    try:
        if args.command=='init':
            init_csv(args.out)
            print('33-country USD ETF quote sheet initialized; ZERO prices')
            return 0
        if args.command=='review':
            draft=json.loads(args.issue.read_text(encoding='utf-8'))
            qa=json.loads(args.qa.read_text(encoding='utf-8'))
            manifest=(json.loads(args.asset_manifest.read_text(encoding='utf-8'))
                      if args.asset_manifest else None)
            p=review(draft,qa,manifest)
            args.out_issue.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
            print('SOURCE-LINKED M1 REVIEW CANDIDATE; STILL REQUIRES CEO POST APPROVAL')
            return 0
        candidate=not args.draft_only
        if candidate:
            need(args.brand_logo is not None and args.png is not None and
                 args.mobile_png is not None and args.asset_manifest is not None,
                 'Prompt 2 exact M1 candidate requires approved logo, native PNG, '
                 '390px PNG and asset-manifest; use --draft-only for research')
        p,report=build(args.quotes,args.session_date,args.prior_date,args.cutoff_utc,
                       issue_id=args.issue_id,headline=args.headline,logo=args.brand_logo)
        logo=checked_logo(args.brand_logo) if args.brand_logo else None
        if candidate:
            p['artifact_intent']='EXACT_ARTIFACT_AWAITING_PROMPT3'
            p['caption_review_state']='EXACT_CANDIDATE_AWAITING_PROMPT3'
        svg=render_global_map(p,logo,
                              status='REVIEW_CANDIDATE' if candidate else 'DRAFT')
        png=None;mobile=None
        if args.png or args.mobile_png:
            import fitz
            doc=fitz.open(stream=svg.encode('utf-8'),filetype='svg')
            page=doc[0]
            if args.png:
                pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
                need((pix.width,pix.height)==(1080,1350),
                     'Unexpected M1 native PNG dimensions')
                png=pix.tobytes('png')
            if args.mobile_png:
                pix=page.get_pixmap(matrix=fitz.Matrix(390/1080,390/1080),alpha=False)
                need(pix.width==390 and pix.height>=487,
                     'Unexpected M1 390px mobile proof dimensions')
                mobile=pix.tobytes('png')
            doc.close()
        manifest=(exact_asset_manifest(p,args.quotes,args.svg,svg,args.png,png,
                                       args.mobile_png,mobile)
                  if candidate else None)
        if candidate:
            report.update(state='EXACT_FINAL_LOOK_AWAITING_PROMPT3_AND_CEO',
                          issue_sha256=payload_hash(p),
                          caption_sha256=manifest['caption_sha256'],
                          png_sha256=manifest['assets']['png']['sha256'],
                          mobile_png_sha256=manifest['assets']['mobile_png']['sha256'])
        # Finish validation and byte hashing BEFORE writing any output files.
        output_items=[(args.out_issue,json.dumps(p,indent=2)+'\n'),
                      (args.svg,svg),(args.png,png),(args.mobile_png,mobile)]
        if candidate:
            output_items.append((args.asset_manifest,json.dumps(manifest,indent=2)+'\n'))
        need(len({dest.resolve() for dest,_ in output_items if dest})==
             len([dest for dest,_ in output_items if dest]),
             'M1 output file paths must be distinct')
        for dest,content in output_items:
            if dest and content is not None:
                dest.parent.mkdir(parents=True,exist_ok=True)
                if isinstance(content,str):
                    dest.write_text(content,encoding='utf-8')
                else:
                    dest.write_bytes(content)
        print(json.dumps(report,sort_keys=True))
        return 0
    except (InvalidIssue,OSError,ValueError,TypeError,KeyError,ImportError) as err:
        print('HOLD:',err,file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
