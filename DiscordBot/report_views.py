import discord
from discord import ui

ABUSE_TYPES = [
    "Bullying or harassment",
    "Scam or fraud",
    "Suicide or self-injury",
    "Violence or dangerous organizations",
    "Hate speech or symbols",
    "Nudity or sexual activity",
    "Spam",
    "Other reason",
]
HARASSMENT_TYPES = [
    "Impersonation",
    "Threat",
    "Hate speech",
    "Flaming",
    "Denigration",
    "Revealing Private Info",
    "Blackmailing",
    "Other",
]


class ButtonView(ui.View):
    """General View to handle a view containing buttons."""

    def __init__(self, report):
        super().__init__()
        self.report = report

    async def change_buttons(self, interaction, button):
        """Disable buttons and change `button` to green."""
        self.disable_buttons()
        button.style = discord.ButtonStyle.success
        await interaction.response.edit_message(view=self)

    def disable_buttons(self):
        """Disables all the buttons in the View and turns them grey."""
        for button in self.children:
            button.disabled = True
            button.style = discord.ButtonStyle.grey


class AnythingElse(ButtonView):
    """View to handle if the user has any other information."""

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.primary)
    async def submit_callback(self, interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(embed=self.report.create_submit_embed())
        await self.report.finish_report()

    @discord.ui.button(label="Add description", style=discord.ButtonStyle.secondary)
    async def more_button_callback(self, interaction, button):
        await self.change_buttons(interaction, button)
        self.report.set_info_state()
        await interaction.followup.send(
            "Please share any additional info you have.\nYour report will be automatically submitted afterwards."
        )


class MoreInfoView(ButtonView):
    """View to handle if you'd like to provide extra message IDs."""

    @discord.ui.button(label="No", style=discord.ButtonStyle.primary)
    async def submit_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(
            "Is there anything else you would like the moderators to know?\nIf not, your report will be submitted.",
            view=AnythingElse(self.report),
        )

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.secondary)
    async def more_button_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        self.report.set_msg_id_state()
        await interaction.followup.send(
            "Please copy paste the link to the message you want to report.\nYou can obtain this link by right-clicking the message and clicking Copy Message Link."
        )


class SubmitOrInfoView(ButtonView):
    """View to handle earliest submission."""

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.primary)
    async def submit_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(embed=self.report.create_submit_embed())
        await self.report.finish_report()

    @discord.ui.button(label="More Info", style=discord.ButtonStyle.secondary)
    async def more_button_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(
            "Sure. Is there another message you would like to add to this report?",
            view=MoreInfoView(self.report),
        )


class HarassmentTypesView(ui.View):
    """View to handle the selection of the harassment type."""

    def __init__(self, report):
        super().__init__()
        self.report = report

    @discord.ui.select(
        placeholder="Select type of harassment...",
        options=[discord.SelectOption(label=h) for h in HARASSMENT_TYPES],
        max_values=len(HARASSMENT_TYPES),
    )
    async def select_callback(self, interaction: discord.Interaction, select):
        self.report.set_harassment_types(select.values)

        # Disable Selection
        select.disabled = True
        await interaction.response.edit_message(view=self)

        # Create next view
        selection_msg = (
            "You selected the following: " + ", ".join(select.values) + ".\n\n"
        )
        await interaction.followup.send(
            selection_msg
            + "Would you like to submit your report or provide more information?",
            view=SubmitOrInfoView(self.report),
        )


class OtherVictimSelect(ui.Select):
    """Select (NOT View!) to handle selection of other person being harassed."""

    def __init__(self, report):
        super().__init__(
            placeholder="Please select the user...",
            options=[
                discord.SelectOption(label=member.name)
                for member in report.message.channel.members
            ],
        )
        self.report = report

    async def callback(self, interaction: discord.Interaction):
        self.report.set_target(self.values[0])
        # Disable Selection
        self.disabled = True
        self.placeholder = self.values[0]
        new_view = ui.View()
        new_view.add_item(self)
        await interaction.response.edit_message(view=new_view)

        # Create harassment type selection view
        selection_msg = "You selected " + self.values[0] + ".\n\n"
        await interaction.followup.send(
            selection_msg
            + "What kinds of harassment did "
            + self.values[0]
            + " experience? Select all that apply.",
            view=HarassmentTypesView(self.report),
        )


class VictimView(ButtonView):
    """View to handle who is being harassed."""

    @discord.ui.button(label="Me", style=discord.ButtonStyle.primary)
    async def me_button_callback(self, interaction, button):
        self.report.set_target("Me")
        await self.change_buttons(interaction, button)
        await interaction.followup.send(
            "You selected 'Me'.\n\nWhat kinds of harassment did you experience? Select all that apply.",
            view=HarassmentTypesView(self.report),
        )

    @discord.ui.button(label="Someone Else", style=discord.ButtonStyle.secondary)
    async def other_button_callback(self, interaction, button):
        await self.change_buttons(interaction, button)
        select = OtherVictimSelect(self.report)
        view = ui.View()
        view.add_item(select)
        await interaction.followup.send(
            "You selected 'Someone Else'.\n\nWho is being bullied?",
            view=view,
        )


class StartView(ui.View):
    """
    Starting point into the user report flow via views.
    View to handle abuse type selection.

    See https://discordpy.readthedocs.io/en/latest/interactions/api.html?highlight=select#id2 for how to create your own.
    """

    def __init__(self, report):
        super().__init__()
        self.report = report

    @discord.ui.select(
        placeholder="Select abuse type...",
        options=[discord.SelectOption(label=abuse) for abuse in ABUSE_TYPES],
    )
    async def select_callback(self, interaction: discord.Interaction, select):
        self.report.set_abuse_type(select.values[0])

        # Disable Selection
        select.disabled = True
        select.placeholder = select.values[0]
        await interaction.response.edit_message(view=self)

        # Handle flows that are not 'bullying and harassment' differently.
        selection_msg = (
            "You selected " + interaction.data["values"][0].lower() + ".\n\n"
        )
        if select.values[0] != ABUSE_TYPES[0]:
            await interaction.followup.send(
                selection_msg
                + "Would you like to submit your report or provide more information?",
                view=SubmitOrInfoView(self.report),
            )
        else:
            # Create next view
            await interaction.followup.send(
                selection_msg + "Who is being bullied or harassed?",
                view=VictimView(self.report),
            )
