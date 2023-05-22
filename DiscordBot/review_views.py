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

    async def change_buttons(self, interaction: discord.Interaction, button):
        """Disable buttons and change `button` to green."""
        self.disable_buttons()
        button.style = discord.ButtonStyle.success
        await interaction.response.edit_message(view=self)

    def disable_buttons(self):
        """Disables all the buttons in the View and turns them grey."""
        for button in self.children:
            button.disabled = True
            button.style = discord.ButtonStyle.grey


class AdversarialView(ButtonView):
    """View to handle whether report is adversarial."""

    @discord.ui.button(label="No", style=discord.ButtonStyle.primary)
    async def risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await self.review.finish_review()

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.secondary)
    async def no_risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        # TODO: consequences


class AdversarialFlaggedView(ButtonView):
    """View to handle whether flagged as adversarial. Should be automated in Milestone 3."""

    @discord.ui.button(label="No", style=discord.ButtonStyle.primary)
    async def risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await self.review.finish_review()

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.secondary)
    async def no_risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(
            "After a manual investigation, is this a case of adversarial reporting?",
            view=AdversarialView(self.review),
        )


class TypeOfViolationView(ButtonView):
    """View to handle which type of violation it is."""

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.primary)
    async def risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        # TODO: consequences

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def no_risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        # TODO: add strike and check strikes
        # TODO: consequences


class IsRiskView(ButtonView):
    """View to handle whether user is at risk."""

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.primary)
    async def risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(
            "Please write a report and forward relevant information to law enforcement."
        )
        # TODO: consequences

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def no_risk_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(
            "Is this an impersonation, threat, hate speech, private info, or blackmailing violation?",
            view=TypeOfViolationView(self.review),
        )


class IsAccurateView(ButtonView):
    """View to handle whether report is accurate."""

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.primary)
    async def accurate_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        await interaction.followup.send(
            "Is the user(s) in immediate or actionable danger / risk of harm?",
            view=IsRiskView(self.review),
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def not_accurate_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        # TODO: automate this step.
        await interaction.followup.send(
            "Is this report flagged as possible adversarial activity?",
            view=AdversarialFlaggedView(self.review),
        )


class ReviewStart(ButtonView):
    """View to handle which report to review."""

    @discord.ui.button(label="Most Urgent", style=discord.ButtonStyle.primary)
    async def urgent_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        (score, report) = self.review.client.pop_highest_priority_report()
        self.review.set_score(score)
        self.review.set_report(report)
        await interaction.followup.send(
            "Is the following report accurate for Bullying or Harassment?",
            embed=create_embed(report),
            view=IsAccurateView(self.review),
        )

    @discord.ui.button(label="Oldest", style=discord.ButtonStyle.secondary)
    async def oldest_callback(self, interaction: discord.Interaction, button):
        await self.change_buttons(interaction, button)
        (score, report) = self.review.client.pop_oldest_report()
        self.review.set_score(score)
        self.review.set_report(report)
        await interaction.followup.send(
            "Is the following report accurate for Bullying or Harassment?",
            embed=create_embed(report),
            view=IsAccurateView(self.review),
        )
