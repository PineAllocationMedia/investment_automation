"""M1 alternative: US-listed unhedged single-country ETF USD market-price map.

This is explicitly NOT a national stock exchange / local-currency index map.
The product list below contains candidate fund identities, NOT guaranteed daily
quotes, exchange price completeness, issuer licenses or rights approvals.
"""
import math
import re
from datetime import timedelta
from urllib.parse import urlparse

from render_global_index_map import (
    COUNTRIES, GEO_VERSION, UPSTREAM_NE_BLOB_SHA, ISSUE_RE,
    MISSING, _dt, _return, _one_number,
)
from render_macro_lens import need, bounded, valid_url

ETF_BASIS = 'US_LISTED_COUNTRY_ETF_USD_MARKET_PRICE_RETURN'
ETF_COMPARISON = 'ONE_COMPLETED_US_ETF_SESSION'
ETF_PRICE_BASIS = 'UNADJUSTED_US_EXCHANGE_CLOSE'
CORPORATE_ACTION = 'NO_MATERIAL_SPLIT_OR_EX_DISTRIBUTION'
ISHARES = 'https://www.ishares.com/us/products/etf-investments'
VANGUARD = 'https://investor.vanguard.com/investment-products/etfs/profile/voo'
VANECK = 'https://www.vaneck.com/us/en/investments/vietnam-etf-vnm/'
# Candidate identity and U.S. fund issuer verified at issuer/SEC sources.
# Fund activity on the target date, underlying country purity, primary quote
# and legal rights still need issue-specific verification.
CANDIDATE_PAIRS = (
    ('USA','VOO','Vanguard S&P 500 ETF','Vanguard',VANGUARD),
    ('JPN','EWJ','iShares MSCI Japan ETF','iShares',ISHARES),
    ('CHN','MCHI','iShares MSCI China ETF','iShares',ISHARES),
    ('IND','INDA','iShares MSCI India ETF','iShares',ISHARES),
    ('DEU','EWG','iShares MSCI Germany ETF','iShares',ISHARES),
    ('GBR','EWU','iShares MSCI UK ETF','iShares',ISHARES),
    ('CAN','EWC','iShares MSCI Canada ETF','iShares',ISHARES),
    ('AUS','EWA','iShares MSCI Australia ETF','iShares',ISHARES),
    ('TWN','EWT','iShares MSCI Taiwan ETF','iShares',ISHARES),
    ('KOR','EWY','iShares MSCI Korea ETF','iShares',ISHARES),
    ('BRA','EWZ','iShares MSCI Brazil ETF','iShares',ISHARES),
    ('FRA','EWQ','iShares MSCI France ETF','iShares',ISHARES),
    ('CHE','EWL','iShares MSCI Swiss ETF','iShares',ISHARES),
    ('MEX','EWW','iShares MSCI Mexico ETF','iShares',ISHARES),
    ('ESP','EWP','iShares MSCI Spain ETF','iShares',ISHARES),
    ('ITA','EWI','iShares MSCI Italy ETF','iShares',ISHARES),
    ('NLD','EWN','iShares MSCI Netherlands ETF','iShares',ISHARES),
    ('SGP','EWS','iShares MSCI Singapore ETF','iShares',ISHARES),
    ('ZAF','EZA','iShares MSCI South Africa ETF','iShares',ISHARES),
    ('TUR','TUR','iShares MSCI Turkey ETF','iShares',ISHARES),
    ('SAU','KSA','iShares MSCI Saudi Arabia ETF','iShares',ISHARES),
    ('IDN','EIDO','iShares MSCI Indonesia ETF','iShares',ISHARES),
    ('VNM','VNM','VanEck Vietnam ETF','VanEck',VANECK),
    ('POL','EPOL','iShares MSCI Poland ETF','iShares',ISHARES),
    ('SWE','EWD','iShares MSCI Sweden ETF','iShares',ISHARES),
)
ETF_CANDIDATES={c:{'ticker':t,'name':n,'issuer':issuer,'issuer_url':url}
                for c,t,n,issuer,url in CANDIDATE_PAIRS}
NO_ETF_PROXY={'EGY','DZA','RUS','KAZ','IRN'}
assert len(ETF_CANDIDATES)==25 and set(ETF_CANDIDATES)|NO_ETF_PROXY==set(COUNTRIES)
# EGPT liquidated in March 2024 (SEC), RSX began liquidation after Russian
# equity market suspension. No stale delisted tickers or broad-region substitutes.


def validate_country_etf_issue(p, geo):
    need(isinstance(p,dict) and p.get('schema_version')=='1.0'
         and p.get('template')=='M1', 'ETF M1 issue/schema required')
    need(p.get('account')=='@therealpam', 'ETF M1 account must be @therealpam')
    need(isinstance(p.get('issue_id'),str) and ISSUE_RE.fullmatch(p['issue_id']),
         'ETF M1 issue ID invalid')
    cutoff=_dt(p.get('cutoff_utc'),'cutoff_utc')
    need(cutoff.utcoffset().total_seconds()==0, 'ETF M1 cutoff must be UTC')
    for k,n in (('headline',62),('deck',111),('interpretation',97),
                ('caption',1200),('universe_version',57),
                ('method_version',45)):
        bounded(p.get(k),k,n)
    need(p.get('selection_basis')=='CEO_SELECTED_30_COUNTRIES',
         'ETF M1 requires all 30 CEO country decisions')
    need(p.get('return_basis')==ETF_BASIS and
         p.get('comparison_basis')==ETF_COMPARISON,
         'ETF M1 requires same U.S. market-price session in USD')
    need(p.get('geometry_version')==GEO_VERSION and
         p.get('geometry_source_github_blob_sha')==UPSTREAM_NE_BLOB_SHA,
         'ETF M1 geodata not pinned')
    need(p.get('rights_note') in ('SYNTHETIC_LAYOUT_ONLY','REVIEWED_FOR_EXACT_USE'),
         'ETF rights status invalid')
    demo=p['rights_note']=='SYNTHETIC_LAYOUT_ONLY'
    need(p.get('scan_status')==('SYNTHETIC_NOT_RUN' if demo else 'COMPLETE_AUDITED'),
         'ETF M1 complete externally reviewed 30-market scan status required')
    need(p.get('universe_review')==('CEO_SELECTED_UNVERIFIED' if demo
                                   else 'COVERAGE_VALIDATED'),
         'ETF M1 universe review invalid')
    need(p.get('benchmark_registry_status')==('CANDIDATES_UNVERIFIED' if demo
                                              else 'INDEPENDENTLY_VERIFIED'),
         'ETF M1 fund identity/activity not independently confirmed')
    need(p.get('etf_price_basis')==ETF_PRICE_BASIS,
         'ETF M1 must use exchange market price, not NAV or total-return')
    need(p.get('fund_currency')=='USD', 'ETF M1 must use USD quote currency')
    rows=p.get('evidence')
    need(isinstance(rows,list) and len(rows)==30,
         'ETF M1 requires full 30-decision evidence register')
    world={f['id'] for f in geo['features']}
    accepted=[];session_dates=set();prior_dates=set();close_times=set()
    for i,e in enumerate(rows):
        code=COUNTRIES[i];name=f'ETF evidence[{i}]'
        need(isinstance(e,dict) and e.get('selection_order')==i+1 and
             e.get('economy_id')==code,
             name+' country/order missing or substituted')
        need(e.get('geometry_id')==('SGP_POINT' if code=='SGP' else code) and
             (code=='SGP' or code in world),
             name+' geometry join invalid')
        bounded(e.get('economy_name'),name+'.economy_name',36)
        bounded(e.get('instrument_name'),name+'.instrument_name',43)
        bounded(e.get('instrument_provider'),name+'.instrument_provider',37)
        bounded(e.get('benchmark_definition'),name+'.benchmark_definition',120)
        bounded(e.get('country_exposure_note'),name+'.country_exposure_note',100)
        bounded(e.get('source_title'),name+'.source_title',50)
        bounded(e.get('rights_note'),name+'.rights_note',160)
        bounded(e.get('verification_note'),name+'.verification_note',160)
        need(e.get('return_currency')=='USD' and
             e.get('listed_currency')=='USD',
             name+' cannot mix local-index or non-USD returns')
        need(e.get('verification')==('DEMO_ONLY' if demo else 'VERIFIED'),
             name+' reviewer assertion missing')
        state=e.get('missing_status')
        need(state=='ELIGIBLE' or state in MISSING,
             name+' eligibility decision missing')
        candidate=ETF_CANDIDATES.get(code)
        if not candidate:
            need(code in NO_ETF_PROXY and
                 e.get('instrument_kind')=='UNAVAILABLE' and
                 e.get('etf_ticker') is None and state!='ELIGIBLE',
                 name+' has no confirmed live single-country U.S. ETF')
            need(e.get('benchmark_variant')=='NO_PROXY',
                 name+' no-proxy status required')
        else:
            need(e.get('instrument_kind')=='ETF' and
                 e.get('etf_ticker')==candidate['ticker'] and
                 e.get('instrument_name')==candidate['name'] and
                 e.get('instrument_provider')==candidate['issuer'] and
                 e.get('issuer_product_url')==candidate['issuer_url'],
                 name+' candidate ticker/issuer/country mismatch')
            need(e.get('benchmark_variant')=='ETF_EXCHANGE_PRICE',
                 name+' ETF exchange-price variant only')
        need(e.get('proxy_scope')=='SINGLE_COUNTRY_UNHEDGED',
             name+' hedged or multi-country substitutes prohibited')
        src=e.get('original_price_source_url')
        if state=='ELIGIBLE' or src is not None:
            valid_url(src,name+'.original_price_source_url')
            domain=urlparse(src).hostname
            if demo:
                need(domain in ('example.org','example.com'),
                     name+' DEMO source must be visibly fictitious')
            else:
                need(domain not in ('example.org','example.com'),
                     name+' source cannot be placeholder')
        if state=='ELIGIBLE':
            need(candidate is not None,
                 name+' missing/defunct ETF cannot be plotted')
            need(e.get('session_status')=='COMPLETED',
                 name+' intraday quote cannot be a completed return')
            need(e.get('etf_price_basis')==ETF_PRICE_BASIS and
                 e.get('corporate_action_review')==CORPORATE_ACTION,
                 name+' split/ex-distribution events not cleared')
            now=_dt(e.get('observed_at'),name+'.observed_at')
            prior=_dt(e.get('prior_observed_at'),name+'.prior_observed_at')
            fetched=_dt(e.get('retrieved_at'),name+'.retrieved_at')
            need(prior<now<=fetched<=cutoff and
                 cutoff-now<=timedelta(hours=96),
                 name+' missing/late/stale original U.S. ETF quote')
            # U.S. exchange closing times, not source-country sessions;
            # record true 16:00 ET offsets rather than blindly using UTC.
            need(now.hour==16 and prior.hour==16 and
                 now.utcoffset().total_seconds() in (-4*3600,-5*3600)
                 and prior.utcoffset().total_seconds() in (-4*3600,-5*3600),
                 name+' expected completed 16:00 U.S. ET ETF close')
            need(now.date().isoformat()==e.get('close_session_date') and
                 prior.date().isoformat()==e.get('prior_session_date'),
                 name+' U.S. session date mismatch')
            _one_number(e,'close_price',name)
            _one_number(e,'prior_close_price',name)
            computed=_return(e)
            need(abs(computed)<=20 and type(e.get('signed_return_pct')) in (int,float)
                 and math.isfinite(e['signed_return_pct']) and
                 abs(computed-e['signed_return_pct'])<=0.005,
                 name+' arithmetic mismatch or extraordinary jump: HOLD')
            accepted.append(e)
            session_dates.add(e['close_session_date'])
            prior_dates.add(e['prior_session_date'])
            close_times.add(now.isoformat())
        else:
            need(e.get('close_price') is None and
                 e.get('prior_close_price') is None and
                 e.get('signed_return_pct') is None,
                 name+' missing cannot be fabricated as 0%')
            need(e.get('session_status')!='COMPLETED',
                 name+' excluded ETF cannot claim completed market quote')
    need(len(accepted)>=4,'ETF M1 requires at least four qualified proxies')
    need(len(session_dates)==1 and len(prior_dates)==1 and len(close_times)==1,
         'ETF M1 all shown ETFs must share one completed U.S. session close')
    return accepted
