from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple
from zoneinfo import available_timezones

import pycountry


MAX_DISCORD_OPTIONS: int = 25


@dataclass(frozen=True)
class CountryOption:
    code: str
    name: str


@dataclass(frozen=True)
class TimezoneOption:
    region: str
    timezone: str
    label: str


EXCLUDED_TIMEZONE_PREFIXES: tuple[str, ...] = (
    "Etc/",
    "Factory",
    "GMT",
    "UCT",
    "Universal",
    "Zulu",
    "posix/",
    "right/",
)


VALID_TOP_LEVEL_REGIONS: set[str] = {
    "Africa",
    "America",
    "Antarctica",
    "Asia",
    "Atlantic",
    "Australia",
    "Europe",
    "Indian",
    "Pacific",
}


def get_all_countries() -> List[CountryOption]:
    """
    Return all ISO-3166 countries from pycountry, sorted by display name.
    """
    countries: List[CountryOption] = []

    for country in pycountry.countries:
        alpha_2: str | None = getattr(country, "alpha_2", None)
        name: str | None = getattr(country, "name", None)

        if not alpha_2 or not name:
            continue

        countries.append(CountryOption(code=alpha_2, name=name))

    return sorted(countries, key=lambda c: c.name.casefold())


def split_countries_into_groups(
    countries: List[CountryOption],
    group_size: int = MAX_DISCORD_OPTIONS,
) -> Dict[str, List[CountryOption]]:
    """
    Split countries into alphabetical groups small enough for Discord select menus.

    Example output keys:
        A-C
        D-F
        G-I
        ...
    """
    if group_size < 1:
        raise ValueError("group_size must be >= 1")

    sorted_countries: List[CountryOption] = sorted(countries, key=lambda c: c.name.casefold())
    grouped: Dict[str, List[CountryOption]] = {}

    for start_index in range(0, len(sorted_countries), group_size):
        chunk: List[CountryOption] = sorted_countries[start_index : start_index + group_size]
        first_letter: str = chunk[0].name[0].upper()
        last_letter: str = chunk[-1].name[0].upper()
        label: str = f"{first_letter}-{last_letter}"
        grouped[label] = chunk

    return grouped


def get_all_timezones() -> List[str]:
    """
    Return filtered IANA timezones from the runtime's zoneinfo database.
    """
    results: List[str] = []

    for tz in sorted(available_timezones()):
        if tz.startswith(EXCLUDED_TIMEZONE_PREFIXES):
            continue

        top_level: str = tz.split("/", 1)[0]
        if top_level not in VALID_TOP_LEVEL_REGIONS:
            continue

        results.append(tz)

    return results


def friendly_timezone_label(timezone_name: str) -> str:
    """
    Convert a raw IANA timezone name into a friendlier label for Discord.
    Example:
        America/New_York -> New York
        Europe/Los_Angeles -> Los Angeles (not a real zone, but you get the idea)
        America/Indiana/Knox -> Indiana / Knox
    """
    parts: List[str] = timezone_name.split("/")

    if len(parts) == 1:
        return parts[0].replace("_", " ")

    # Drop the top-level region and prettify the rest
    readable_parts: List[str] = [part.replace("_", " ") for part in parts[1:]]
    return " / ".join(readable_parts)


def get_timezones_grouped_by_region() -> Dict[str, List[TimezoneOption]]:
    """
    Return timezones grouped by top-level IANA region.
    Example keys:
        America
        Europe
        Asia
    """
    grouped: Dict[str, List[TimezoneOption]] = defaultdict(list)

    for tz in get_all_timezones():
        region: str = tz.split("/", 1)[0]
        grouped[region].append(
            TimezoneOption(
                region=region,
                timezone=tz,
                label=friendly_timezone_label(tz),
            )
        )

    # Sort each region by human-readable label
    for region, values in grouped.items():
        grouped[region] = sorted(values, key=lambda t: t.label.casefold())

    return dict(grouped)


def split_timezone_region_if_needed(
    timezone_options: List[TimezoneOption],
    max_group_size: int = MAX_DISCORD_OPTIONS,
) -> Dict[str, List[TimezoneOption]]:
    """
    Split one large region's timezones into smaller Discord-safe chunks.

    Example keys:
        A-F
        G-M
        N-S
        T-Z
    """
    if max_group_size < 1:
        raise ValueError("max_group_size must be >= 1")

    sorted_timezones: List[TimezoneOption] = sorted(
        timezone_options,
        key=lambda t: t.label.casefold(),
    )
    grouped: Dict[str, List[TimezoneOption]] = {}

    for start_index in range(0, len(sorted_timezones), max_group_size):
        chunk: List[TimezoneOption] = sorted_timezones[start_index : start_index + max_group_size]
        first_letter: str = chunk[0].label[0].upper()
        last_letter: str = chunk[-1].label[0].upper()
        label: str = f"{first_letter}-{last_letter}"
        grouped[label] = chunk

    return grouped


def get_timezone_region_names() -> List[str]:
    """
    Return available top-level timezone regions sorted alphabetically.
    """
    regions: List[str] = list(get_timezones_grouped_by_region().keys())
    return sorted(regions, key=str.casefold)