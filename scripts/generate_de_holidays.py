"""One-off generator for seeds/de_public_holidays.csv.

Not part of the regular pipeline — its output is a committed dbt seed, so
this only needs re-running if the date range or holiday rules change.

Movable feasts are computed from Easter Sunday via the Meeus/Jones/Butcher
Gregorian algorithm. State assignment is a deliberate simplification of a
few edge cases: most notably Mariä Himmelfahrt is legally a
municipality-level holiday in majority-Catholic parts of Bayern, treated
here as statewide, and a couple of recently-added state holidays (Frauentag
in Berlin/Mecklenburg-Vorpommern, Weltkindertag in Thüringen) are applied
across the whole range rather than from their actual introduction year.
"""

import csv
from datetime import date, timedelta
from pathlib import Path

START_YEAR = 2015
END_YEAR = 2031
OUT_PATH = Path("seeds/de_public_holidays.csv")

ALL_STATES = [
    "DE-BW",
    "DE-BY",
    "DE-BE",
    "DE-BB",
    "DE-HB",
    "DE-HH",
    "DE-HE",
    "DE-MV",
    "DE-NI",
    "DE-NW",
    "DE-RP",
    "DE-SL",
    "DE-SN",
    "DE-ST",
    "DE-SH",
    "DE-TH",
]

STATE_HOLIDAYS = {
    "Heilige Drei Könige": ["DE-BW", "DE-BY", "DE-ST"],
    "Fronleichnam": ["DE-BW", "DE-BY", "DE-HE", "DE-NW", "DE-RP", "DE-SL"],
    "Mariä Himmelfahrt": ["DE-BY", "DE-SL"],
    "Weltkindertag": ["DE-TH"],
    "Reformationstag": [
        "DE-BB",
        "DE-HB",
        "DE-HH",
        "DE-MV",
        "DE-NI",
        "DE-SN",
        "DE-ST",
        "DE-SH",
        "DE-TH",
    ],
    "Allerheiligen": ["DE-BW", "DE-BY", "DE-NW", "DE-RP", "DE-SL"],
    "Buß- und Bettag": ["DE-SN"],
    "Internationaler Frauentag": ["DE-BE", "DE-MV"],
}


def easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month = (h + ll - 7 * m + 114) // 31
    day = ((h + ll - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def buss_und_bettag(year: int) -> date:
    nov_22 = date(year, 11, 22)
    offset = (nov_22.weekday() - 2) % 7  # Wednesday == 2
    return nov_22 - timedelta(days=offset)


def holidays_for_year(year: int) -> list[tuple[date, str, bool]]:
    easter = easter_sunday(year)

    nationwide = [
        (date(year, 1, 1), "Neujahr"),
        (easter - timedelta(days=2), "Karfreitag"),
        (easter + timedelta(days=1), "Ostermontag"),
        (date(year, 5, 1), "Tag der Arbeit"),
        (easter + timedelta(days=39), "Christi Himmelfahrt"),
        (easter + timedelta(days=50), "Pfingstmontag"),
        (date(year, 10, 3), "Tag der Deutschen Einheit"),
        (date(year, 12, 25), "1. Weihnachtsfeiertag"),
        (date(year, 12, 26), "2. Weihnachtsfeiertag"),
    ]

    regional = [
        (date(year, 1, 6), "Heilige Drei Könige"),
        (easter + timedelta(days=60), "Fronleichnam"),
        (date(year, 8, 15), "Mariä Himmelfahrt"),
        (date(year, 9, 20), "Weltkindertag"),
        (date(year, 10, 31), "Reformationstag"),
        (date(year, 11, 1), "Allerheiligen"),
        (buss_und_bettag(year), "Buß- und Bettag"),
        (date(year, 3, 8), "Internationaler Frauentag"),
    ]

    rows: list[tuple[date, str, bool]] = [(d, name, True) for d, name in nationwide]
    rows.extend((d, name, False) for d, name in regional)
    return rows


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["holiday_date", "holiday_name", "federal_state", "nationwide"])
        for year in range(START_YEAR, END_YEAR + 1):
            for holiday_date, name, nationwide in holidays_for_year(year):
                states = ALL_STATES if nationwide else STATE_HOLIDAYS[name]
                for state in states:
                    writer.writerow(
                        [holiday_date.isoformat(), name, state, str(nationwide).lower()]
                    )
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
