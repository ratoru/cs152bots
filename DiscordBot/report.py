from enum import Enum, auto
import discord
import re
from report_views import (
    StartView,
    MoreInfoView,
    ABUSE_TYPES,
    HARASSMENT_TYPES,
)
from typing import Optional, List, Union
from datetime import date


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    IN_VIEW = auto()
    GETTING_MSG_ID = auto()
    GETTING_EXTRA_INFO = auto()
    REPORT_CANCELED = auto()
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    SUBMIT_MSG = "Thank you for reporting. We take your report very seriously. Our content moderation team will review your report. Further action might include temporary or permanent account suspension."

    def __init__(self, client):
        # State to handle inner working of bot
        self.state = State.REPORT_START
        # The ModBot
        self.client = client
        # State for filing a report
        self.author = None  # Author of the report
        self.message: discord.Message = None  # Reported message
        self.abuse_type: ABUSE_TYPES = None
        self.harassment_types: List[HARASSMENT_TYPES] = []
        self.target = ""  # Target of the abuse
        self.date_submitted = None
        self.additional_msgs: List[discord.Message] = []
        self.additional_info: Optional[str] = None

    async def handle_message(self, message):
        """
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord.
        """

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_CANCELED
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            self.author = message.author
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
            msg = await self.parse_msg(message)
            if type(msg) == str:
                return [msg]

            if self.client.is_banned(msg.author):
                return [
                    "This user is already banned.",
                    "Please provide a different message.",
                ]

            # Here we've found the message - let's enter our View flow.
            self.state = State.IN_VIEW
            self.message = msg
            return [
                "I found this message:",
                "```" + msg.author.name + ": " + msg.content + "```",
                ("Why would you like to report this message?", StartView(report=self)),
            ]

        if self.state == State.GETTING_MSG_ID:
            msg = await self.parse_msg(message)
            if type(msg) == str:
                return [msg]
            self.additional_msgs.append(msg)
            self.state = State.IN_VIEW
            return [
                "I found this message to add to the report:",
                "```" + msg.author.name + ": " + msg.content + "```",
                (
                    "Is there another message you would like to add to this report?",
                    MoreInfoView(report=self),
                ),
            ]

        if self.state == State.GETTING_EXTRA_INFO:
            self.additional_info = message.content
            self.date_submitted = date.today()
            self.state = State.REPORT_COMPLETE
            return [("", self.create_submit_embed())]

        if self.state == State.IN_VIEW:
            # If there is a view, the view should be interacted with.
            return [
                "Sorry, you are in the middle of a report.\nContinue by selecting an option above or stop by typing `cancel`."
            ]

        return []

    async def parse_msg(self, message: discord.Message) -> Union[discord.Message, str]:
        """Takes a message link and returns the message object or an error."""
        # Parse out the three ID strings from the message link
        m = re.search("/(\d+)/(\d+)/(\d+)", message.content)
        if not m:
            return "I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."
        guild = self.client.get_guild(int(m.group(1)))
        if not guild:
            return "I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."
        channel = guild.get_channel(int(m.group(2)))
        if not channel:
            return "It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."
        try:
            message = await channel.fetch_message(int(m.group(3)))
        except discord.errors.NotFound:
            return "It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."
        return message

    def report_canceled(self):
        return self.state == State.REPORT_CANCELED

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def create_submit_embed(self):
        """Creates an embed for report submission."""
        embed = discord.Embed(
            title="We received your report!",
            description=self.SUBMIT_MSG,
            color=discord.Color.green(),
        )
        embed.set_author(name="Community Moderators")
        return embed

    def format_extra_msgs(self):
        return ", ".join([f"`{msg.content}`" for msg in self.additional_msgs])

    def report_info(self):
        """Info provided to the moderators for review."""
        return (
            f"User {self.author.name} reported the following message on {self.date_submitted}:\n"
            + f"```{self.message.author.name}: {self.message.content}```\n"
            + f"Abuse Type: {self.abuse_type}\n"
            + f"Harassment Types: {self.harassment_types}\n"
            + f"Target of the abuse: {self.target} \n"
            + f"Additional Msgs: {self.format_extra_msgs()}\n"
            + f"Additional Info: {self.additional_info}"
        )

    async def finish_report(self):
        """Finishes the report by setting the type to complete and calling the client's clean up funciton."""
        self.state = State.REPORT_COMPLETE
        self.date_submitted = date.today()
        await self.client.clean_up_report(self.author.id)

    # State setters and getters
    def set_info_state(self):
        self.state = State.GETTING_EXTRA_INFO

    def set_msg_id_state(self):
        self.state = State.GETTING_MSG_ID

    def set_abuse_type(self, abuse: ABUSE_TYPES):
        self.abuse_type = abuse

    def set_harassment_types(self, harassments: HARASSMENT_TYPES):
        self.harassment_types = harassments

    def set_target(self, target):
        self.target = target

    # Sorting functions for the class
    def _is_valid_operand(self, other):
        return hasattr(other, "date_submitted")

    def __lt__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.date_submitted < other.date_submitted
