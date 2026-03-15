from __future__ import annotations

import discord
from discord.ui import Select, View
from typing import Callable, Awaitable

from data.languages import GAME_LANGUAGES

AsyncCallback = Callable[[discord.Interaction, str], Awaitable[None]]


class LanguageSelect(Select):

    def __init__(self, on_selected: AsyncCallback):

        self._on_selected = on_selected

        options = [
            discord.SelectOption(label=name, value=code)
            for code, name in GAME_LANGUAGES.items()
        ]

        super().__init__(
            placeholder="Select language",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        await self._on_selected(interaction, self.values[0])


class LanguageView(View):

    def __init__(self, on_selected: AsyncCallback):
        super().__init__(timeout=300)
        self.add_item(LanguageSelect(on_selected))