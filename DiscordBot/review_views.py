import discord
from discord import ui


def create_embed(report):
    """Creates an embed containging the passed in report."""
    embed = discord.Embed(
        title=f"Report against {report.target}",
        description=report.report_info(),
        color=discord.Color.yellow(),
    )
    embed.set_author(name=f"User #{report.author_id}")
    return embed


class ButtonView(ui.View):
    """General View to handle a view containing buttons."""

    def __init__(self, review):
        super().__init__()
        self.review = review

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


class ReviewStart(ButtonView):
    """View to handle which report to review."""

    @discord.ui.button(label="Most Urgent", style=discord.ButtonStyle.primary)
    async def submit_callback(self, interaction, button):
        await self.change_buttons(interaction, button)
        (score, report) = self.review.client.pop_highest_priority_report()
        self.review.set_score(score)
        self.review.set_report(report)
        await interaction.followup.send(embed=create_embed(report))

    @discord.ui.button(label="Oldest", style=discord.ButtonStyle.secondary)
    async def more_button_callback(self, interaction, button):
        await self.change_buttons(interaction, button)
        (score, report) = self.review.client.pop_oldest_report()
        self.review.set_score(score)
        self.review.set_report(report)
        await interaction.followup.send(embed=create_embed(report))
