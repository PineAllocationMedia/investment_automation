"""Fictional directory bytes only; never real listing or investment authority."""
T1 = "2026-09-21T12:00:00Z"
T2 = "2026-09-21T12:01:00Z"
HEADER = ("Symbol", "Security Name", "Market Category", "Test Issue",
          "Financial Status", "Round Lot Size", "ETF", "NextShares")
CREATION = "File Creation Time: 0921202611:59"


def row(symbol="FICT", **changes):
    fields = dict(zip(HEADER, (symbol, "Fictional Company - Common Stock", "Q", "N", "N", "100", "N", "N")))
    fields.update(changes)
    return fields


def directory(rows=None, *, header=HEADER, footer=CREATION, newline="\n"):
    rows = [row()] if rows is None else rows
    lines = ["|".join(header)] + ["|".join(value[name] for name in header) for value in rows]
    lines.append(footer + "|" * (len(header) - 1))
    return (newline.join(lines) + newline).encode("utf-8")
