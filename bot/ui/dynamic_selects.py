from __future__ import annotations

from typing import Callable, Awaitable, Dict, List, Optional

import discord
from discord.ui import Select, View

from data.dynamic_lookups import (
    CountryOption,
    TimezoneOption,
    get_all_countries,
    get_timezone_region_names,
    get_timezones_grouped_by_region,
    split_countries_into_groups,
    split_timezone_region_if_needed,
)


AsyncCallback = Callable[[discord.Interaction, str], Awaitable[None]]


class CountryGroupSelect(Select):
    def __init__(self, on_selected: AsyncCallback) -> None:
        self._on_selected: AsyncCallback = on_selected

        grouped = split_countries_into_groups(get_all_countries())
        options: List[discord.SelectOption] = [
            discord.SelectOption(label=group_name, value=group_name)
            for group_name in grouped.keys()
        ]

        super().__init__(
            placeholder="Select country group",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._on_selected(interaction, self.values[0])


class CountryGroupView(View):
    def __init__(self, on_selected: AsyncCallback) -> None:
        super().__init__(timeout=300)
        self.add_item(CountryGroupSelect(on_selected))


class CountrySelect(Select):
    def __init__(self, group_name: str, on_selected: AsyncCallback) -> None:
        self._on_selected: AsyncCallback = on_selected

        grouped = split_countries_into_groups(get_all_countries())
        countries: List[CountryOption] = grouped[group_name]

        options: List[discord.SelectOption] = [
            discord.SelectOption(label=country.name, value=country.code)
            for country in countries
        ]

        super().__init__(
            placeholder="Select country",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._on_selected(interaction, self.values[0])


class CountrySelectView(View):
    def __init__(self, group_name: str, on_selected: AsyncCallback) -> None:
        super().__init__(timeout=300)
        self.add_item(CountrySelect(group_name, on_selected))


class TimezoneRegionSelect(Select):
    def __init__(self, on_selected: AsyncCallback) -> None:
        self._on_selected: AsyncCallback = on_selected

        options: List[discord.SelectOption] = [
            discord.SelectOption(label=region, value=region)
            for region in get_timezone_region_names()
        ]

        super().__init__(
            placeholder="Select timezone region",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._on_selected(interaction, self.values[0])


class TimezoneRegionView(View):
    def __init__(self, on_selected: AsyncCallback) -> None:
        super().__init__(timeout=300)
        self.add_item(TimezoneRegionSelect(on_selected))


class TimezoneSubgroupSelect(Select):
    def __init__(self, region: str, on_selected: AsyncCallback) -> None:
        self._on_selected: AsyncCallback = on_selected
        self._region: str = region

        grouped = get_timezones_grouped_by_region()
        subgroups = split_timezone_region_if_needed(grouped[region])

        options: List[discord.SelectOption] = [
            discord.SelectOption(label=subgroup_name, value=subgroup_name)
            for subgroup_name in subgroups.keys()
        ]

        super().__init__(
            placeholder=f"Select {region} timezone subgroup",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        subgroup_key: str = self.values[0]
        await self._on_selected(interaction, subgroup_key)


class TimezoneSubgroupView(View):
    def __init__(self, region: str, on_selected: AsyncCallback) -> None:
        super().__init__(timeout=300)
        self.add_item(TimezoneSubgroupSelect(region, on_selected))


class TimezoneSelect(Select):
    def __init__(self, region: str, subgroup_name: str, on_selected: AsyncCallback) -> None:
        self._on_selected: AsyncCallback = on_selected

        grouped = get_timezones_grouped_by_region()
        subgrouped = split_timezone_region_if_needed(grouped[region])
        timezones: List[TimezoneOption] = subgrouped[subgroup_name]

        options: List[discord.SelectOption] = [
            discord.SelectOption(label=tz.label, value=tz.timezone)
            for tz in timezones
        ]

        super().__init__(
            placeholder="Select timezone",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._on_selected(interaction, self.values[0])


class TimezoneSelectView(View):
    def __init__(self, region: str, subgroup_name: str, on_selected: AsyncCallback) -> None:
        super().__init__(timeout=300)
        self.add_item(TimezoneSelect(region, subgroup_name, on_selected))