#!/usr/bin/env python3
"""Fail-closed SVG label check. Does not audit financial facts or rasterized text."""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

INTERNAL_STATUS = re.compile(
    r"\b(?:DRAFT|NOT[\s-]+AUDITED|AUDIT[\s-]+ONLY|"
    r"NOT[\s-]+FOR[\s-]+PUBLICATION|PENDING[\s-]+APPROVAL|"
    r"INTERNAL[\s-]+(?:ONLY|REVIEW)|REVIEW[\s-]+(?:PENDING|REQUIRED)|"
    r"CEO[\s-]+APPROVAL[\s-]+PENDING|WORKING[\s-]+(?:COPY|ASSET))\b",
    re.IGNORECASE,
)


def synthetic_issue(payload):
    if payload.get('rights_note') == 'SYNTHETIC_LAYOUT_ONLY':
        return True
    for fact in payload.get('evidence', []):
        if not isinstance(fact, dict):
            continue
        if 'synthetic' in str(fact.get('verification_note', '')).lower():
            return True
        host = urlparse(str(fact.get('source_url', ''))).hostname
        if host in ('example.org', 'example.com'):
            return True
    return False


def assert_clean_artwork(svg):
    """Inspect SVG text/tspan labels; cannot inspect text embedded as pixels."""
    root = ET.fromstring(svg)
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] != 'text':
            continue
        label = ' '.join(element.itertext()).strip()
        if INTERNAL_STATUS.search(label):
            raise ValueError('Visible internal-status label prohibited: ' + label[:110])


def run(argv=None):
    parser = argparse.ArgumentParser(description='Reject on-artwork draft/review labels')
    parser.add_argument('svg', type=Path)
    args = parser.parse_args(argv)
    try:
        assert_clean_artwork(args.svg.read_text(encoding='utf-8'))
    except (OSError, ValueError, ET.ParseError) as exc:
        print('HOLD: ' + str(exc), file=sys.stderr)
        return 2
    print('PASS: no internal SVG text labels found (inspect actual PNG separately)')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
