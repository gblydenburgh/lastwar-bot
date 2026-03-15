from __future__ import annotations

import discord
from discord.ui import View, Button, Select, Modal, TextInput

from workflows.registration import RegistrationWorkflow


class RegisterButton(Button):
    """
    Button users press to start registration.
    """

    def __init__(self, workflow: RegistrationWorkflow):
        super().__init__(label="Register Profile", style=discord.ButtonStyle.green)
        self.workflow = workflow

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        self.workflow.start(user_id)

        modal = IngameNameModal(self.workflow)
        await interaction.response.send_modal(modal)


class RegistrationView(View):
    """
    Persistent view containing the register button.
    """

    def __init__(self, workflow: RegistrationWorkflow):
        super().__init__(timeout=None)
        self.add_item(RegisterButton(workflow))


class IngameNameModal(Modal):
    """
    First modal: ask for in-game name.
    """

    def __init__(self, workflow: RegistrationWorkflow):
        super().__init__(title="Enter In-Game Name")

        self.workflow = workflow

        self.ingame_name = TextInput(
            label="In-Game Name",
            placeholder="Enter your Last War name",
            required=True,
            max_length=30,
        )

        self.add_item(self.ingame_name)

    async def on_submit(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        self.workflow.store_step_data(
            discord_user_id=user_id,
            step="country",
            data={
                "ingame_name": self.ingame_name.value,
            },
        )

        view = CountrySelectView(self.workflow)

        await interaction.response.send_message(
            "Select your **country**:",
            view=view,
            ephemeral=True,
        )


class CountrySelect(Select):
    """
    Dropdown for country selection.
    """

    def __init__(self, workflow: RegistrationWorkflow):

        options = [
            discord.SelectOption(label="United States", value="US"),
            discord.SelectOption(label="Canada", value="CA"),
            discord.SelectOption(label="United Kingdom", value="GB"),
            discord.SelectOption(label="Germany", value="DE"),
            discord.SelectOption(label="France", value="FR"),
        ]

        super().__init__(
            placeholder="Select your country",
            options=options,
        )

        self.workflow = workflow

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        self.workflow.store_step_data(
            discord_user_id=user_id,
            step="language",
            data={
                "country_code": self.values[0],
            },
        )

        view = LanguageSelectView(self.workflow)

        await interaction.response.edit_message(
            content="Select your **primary language**:",
            view=view,
        )


class CountrySelectView(View):

    def __init__(self, workflow: RegistrationWorkflow):
        super().__init__()
        self.add_item(CountrySelect(workflow))


class LanguageSelect(Select):

    def __init__(self, workflow: RegistrationWorkflow):

        options = [
            discord.SelectOption(label="English", value="EN"),
            discord.SelectOption(label="Spanish", value="ES"),
            discord.SelectOption(label="German", value="DE"),
            discord.SelectOption(label="French", value="FR"),
        ]

        super().__init__(
            placeholder="Select primary language",
            options=options,
        )

        self.workflow = workflow

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        self.workflow.store_step_data(
            discord_user_id=user_id,
            step="timezone",
            data={
                "primary_language_code": self.values[0],
            },
        )

        await interaction.response.send_message(
            "Next step: timezone selection (not implemented yet).",
            ephemeral=True,
        )


class LanguageSelectView(View):

    def __init__(self, workflow: RegistrationWorkflow):
        super().__init__()
        self.add_item(LanguageSelect(workflow))
