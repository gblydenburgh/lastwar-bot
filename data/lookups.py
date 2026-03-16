from __future__ import annotations

from zoneinfo import available_timezones

import pycountry

LANGUAGE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("ru", "Russian"),
    ("tr", "Turkish"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("zh-hans", "Chinese (Simplified)"),
    ("zh-hant", "Chinese (Traditional)"),
    ("ar", "Arabic"),
    ("th", "Thai"),
    ("vi", "Vietnamese"),
    ("id", "Indonesian"),
)

SQUAD_TYPES: tuple[str, ...] = ("tank", "air", "missile", "mixed")
ACCOUNT_TYPES: tuple[str, ...] = ("main", "alt")


def country_choices() -> list[tuple[str, str]]:
    countries: list[tuple[str, str]] = []
    for country in pycountry.countries:
        alpha_2 = getattr(country, "alpha_2", None)
        name = getattr(country, "name", None)
        if alpha_2 and name:
            countries.append((alpha_2, name))
    return sorted(countries, key=lambda item: item[1])


def timezone_choices() -> list[str]:
    return sorted(available_timezones())


def language_codes() -> set[str]:
    return {code for code, _ in LANGUAGE_OPTIONS}


def country_codes() -> set[str]:
    return {code for code, _ in country_choices()}
