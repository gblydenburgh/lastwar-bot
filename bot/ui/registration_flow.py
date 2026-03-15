from __future__ import annotations

import discord

from workflows.registration import RegistrationWorkflow
from bot.ui.dynamic_selects import (
    CountryGroupView,
    CountrySelectView,
    TimezoneRegionView,
    TimezoneSubgroupView,
    TimezoneSelectView,
)
from data.languages import GAME_LANGUAGES


class RegistrationFlow:

    def __init__(self, workflow: RegistrationWorkflow):
        self.workflow = workflow

    async def start_country_flow(self, interaction: discord.Interaction):

        async def country_group_selected(
            inner_interaction: discord.Interaction,
            group_name: str,
        ):
            await inner_interaction.response.edit_message(
                content="Select your **country**.",
                view=CountrySelectView(group_name, country_selected),
            )

        async def country_selected(
            inner_interaction: discord.Interaction,
            country_code: str,
        ):

            user_id = str(inner_interaction.user.id)

            self.workflow.store_step_data(
                discord_user_id=user_id,
                step="language",
                data={"country_code": country_code},
            )

            await inner_interaction.response.edit_message(
                content="Select your **primary language**.",
                view=LanguageView(language_selected),
            )

        async def language_selected(
            inner_interaction: discord.Interaction,
            language_code: str,
        ):

            user_id = str(inner_interaction.user.id)

            self.workflow.store_step_data(
                discord_user_id=user_id,
                step="timezone_region",
                data={"primary_language_code": language_code},
            )

            await inner_interaction.response.edit_message(
                content="Select your **timezone region**.",
                view=TimezoneRegionView(timezone_region_selected),
            )

        async def timezone_region_selected(
            inner_interaction: discord.Interaction,
            region: str,
        ):

            await inner_interaction.response.edit_message(
                content="Select your **timezone subgroup**.",
                view=TimezoneSubgroupView(region, lambda i, s: timezone_subgroup_selected(i, region, s)),
            )

        async def timezone_subgroup_selected(
            inner_interaction: discord.Interaction,
            region: str,
            subgroup: str,
        ):

            await inner_interaction.response.edit_message(
                content="Select your **timezone**.",
                view=TimezoneSelectView(region, subgroup, timezone_selected),
            )

        async def timezone_selected(
            inner_interaction: discord.Interaction,
            timezone_name: str,
        ):

            user_id = str(inner_interaction.user.id)

            self.workflow.store_step_data(
                discord_user_id=user_id,
                step="availability",
                data={"timezone": timezone_name},
            )

            await inner_interaction.response.edit_message(
                content=f"Timezone saved: **{timezone_name}**\n\nNext step: availability window.",
                view=None,
            )

        await interaction.response.send_message(
            "Select your **country group**.",
            view=CountryGroupView(country_group_selected),
            ephemeral=True,
        )