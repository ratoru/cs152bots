# bot.py
import discord
from datetime import date
import os
import json
import logging
import re
from report import Report
from report import State
from review import Review
from statistics import Statistics
import heapq
import perspective
from typing import Literal

# Set up logging to the console
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens["discord"]


class ModBot(discord.Client):
    STRIKE_LIMIT = 3
    AUTOREPORT_THRESHOLD = 0.7
    AUTOSUSPEND_THRESHOLD = 0.8
    AUTOBAN_THRESHOLD = 0.95
    PERFORMANCE_KEYWORD = "performance"
    # PURGE_KEYWORD = "clear"

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = (
            True  # This is to get the list of members in the Group 34 channel
        )
        super().__init__(command_prefix=".", intents=intents)
        self.group_num = None
        self.mod_channel: discord.TextChannel = None  # Mod channel id for that guild
        self.regular_channel: discord.TextChannel = None  # Regular channel id
        self.unfinished_reports = {}  # Map from user IDs to the state of their report
        self.unreviewed_reports = []  # Priority queue storing unreviewed reports
        self.cur_review = None  # Review in progress
        self.banned_users = set()
        self.statistics = Statistics()

    async def on_ready(self):
        print(f"{self.user.name} has connected to Discord! It is these guilds:")
        for guild in self.guilds:
            print(f" - {guild.name}")
        print("Press Ctrl-C to quit.")

        # Parse the group number out of the bot's name
        match = re.search("[gG]roup (\d+) [bB]ot", self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception(
                'Group number not found in bot\'s name. Name format should be "Group # Bot".'
            )

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f"group-{self.group_num}-mod":
                    self.mod_channel = channel
                if channel.name == f"group-{self.group_num}":
                    self.regular_channel = channel

    async def on_message(self, message):
        """
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        """
        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            if message.channel.name == f"group-{self.group_num}":
                await self.handle_normal_channel_message(message)

            if message.channel.name == f"group-{self.group_num}-mod":
                await self.handle_mod_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.unfinished_reports and not message.content.startswith(
            Report.START_KEYWORD
        ):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.unfinished_reports:
            self.unfinished_reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.unfinished_reports[author_id].handle_message(message)
        for r in responses:
            if type(r) is tuple:
                if type(r[1]) is discord.Embed:
                    # Some responses might include an Embed.
                    await message.channel.send(embed=r[1])
                else:
                    # Some responses might include a View.
                    await message.channel.send(r[0], view=r[1])
            else:
                await message.channel.send(r)
        # If the report is complete or cancelled, remove it from our map
        # We do this here just in case the report is not completed by a View callback.
        # View callback's must call `clean_up_report` themselves.
        await self.clean_up_report(author_id)

    async def clean_up_report(self, author_id):
        """
        Performs all necessary steps before a user report is finished.
        If the report is complete or cancelled, remove it from our map.
        """
        if author_id not in self.unfinished_reports:
            return
        # Add completed report to review queue
        if self.unfinished_reports[author_id].report_complete():
            cur_report = self.unfinished_reports[author_id]
            self.push_report(cur_report.score, cur_report)
            await self.mod_channel.send(
                f"There are {len(self.unreviewed_reports)} reports outstanding."
            )
        # Remove report from internal map.
        if (
            self.unfinished_reports[author_id].report_canceled()
            or self.unfinished_reports[author_id].report_complete()
        ):
            self.unfinished_reports.pop(author_id)

    async def handle_normal_channel_message(self, message):
        """Runs our classifier against the message and updates all statistics accordingly.
        Will ban users for extremely hateful comments.
        """
        # if message.content == self.PURGE_KEYWORD:
        #     await self.regular_channel.purge(reason="Clearing messages for video.")
        #     return

        score = perspective.analyze_text(message.content)
        # Sets up the autoreport
        self.statistics.add_sentiment(message.author.id, score)
        if score > self.AUTOBAN_THRESHOLD:
            await self.mod_channel.send(
                f"User `{message.author.name}` got auto-banned for a message with concern score {round(score * 100 , 2)}%."
            )
            await self.ban_user(message.author, message.content, False)
        elif score > self.AUTOSUSPEND_THRESHOLD:
            await self.mod_channel.send(
                f"User `{message.author.name}` got auto-suspended for a message with concern score {round(score * 100 , 2)}%."
            )
            await self.enforce_strike(message.author, message.content, False)
        elif score > self.AUTOREPORT_THRESHOLD:
            autoreport = Report(self)
            autoreport.abuse_type = "Bullying or harrasment"
            autoreport.author = self.user
            autoreport.message = message
            autoreport.score = score
            autoreport.state = State.REPORT_COMPLETE
            autoreport.date_submitted = date.today()
            self.push_report(score, autoreport)
            await self.mod_channel.send(
                f"There are {len(self.unreviewed_reports)} reports outstanding."
            )

    async def handle_mod_channel_message(self, message):
        # Handle a help message
        if message.content == Review.HELP_KEYWORD:
            reply = "Use the `review` command to begin the reviewing process.\n"
            reply += "Use the `cancel` command to cancel the reviewing process.\n"
            reply += "Use the `performance` command to review the accuracy of the API."
            await message.channel.send(reply)
            return

        # Handle checking on the API performance
        if message.content == self.PERFORMANCE_KEYWORD:
            reply = self.statistics.api_statistics_overview()
            await message.channel.send(reply)
            return

        # # Purges all messages in the mod channel
        # if message.content == self.PURGE_KEYWORD:
        #     await self.mod_channel.purge(
        #         limit=None, reason="Clearing messsages for video."
        #     )
        #     return

        # Only respond to messages if they're part of a review flow
        if self.cur_review is None and not message.content.startswith(
            Review.START_KEYWORD
        ):
            return

        # If we don't currently have a review, create one
        if self.cur_review is None:
            self.cur_review = Review(self)

        # Let the review class handle this message; forward all the messages it returns to us
        responses = await self.cur_review.handle_message(message)
        for r in responses:
            if type(r) is tuple:
                # Some responses might include a View.
                await message.channel.send(r[0], view=r[1])
            else:
                await message.channel.send(r)
        # If the review is complete or cancelled, clean up resources
        # We do this here just in case the report is not completed by a View callback.
        # View callback's must call `clean_up_report` themselves.
        await self.clean_up_review()

    def pop_highest_priority_report(self):
        """Pops unreviewed report with the highest priority."""
        score_report = heapq.heappop(self.unreviewed_reports)
        return (-score_report[0], score_report[1])

    def pop_oldest_report(self):
        """Pops oldest unreviewed report."""
        oldest_i = 0
        (oldest_score, oldest_report) = self.unreviewed_reports[0]
        for i, (score, report) in enumerate(self.unreviewed_reports):
            if report.date_submitted < oldest_report.date_submitted:
                oldest_i = i
                oldest_score = score
                oldest_report = report
        del self.unreviewed_reports[oldest_i]
        heapq.heapify(self.unreviewed_reports)
        return (-oldest_score, oldest_report)

    def push_report(self, score, report):
        heapq.heappush(self.unreviewed_reports, (-score, report))

    async def enforce_strike(
        self, user, message_content: str, adversarial: bool
    ) -> bool:
        """
        Adds a strike to the user's account.
        If the user has STRIKE_LIMIT strikes, the user will be banned. Otherwise, the user will be suspended.
        """
        if self.statistics.add_and_check_strike(user.id, self.STRIKE_LIMIT):
            await self.mod_channel.send(
                f"This is the user's 3rd strike. They will be banned..."
            )
            await self.ban_user(
                user,
                message_content,
                adversarial,
            )
        else:
            await self.suspend_user(
                user,
                message_content,
                adversarial,
            )

    async def delete_messages(self, user):
        """Deletes all messages from user `user_id`."""
        deleted = await self.regular_channel.purge(
            check=lambda m: m.author == user, reason="Account Banned"
        )
        await self.mod_channel.send(
            f"{len(deleted)} messages from user {user.name} have been deleted."
        )

    async def delete_associated_reports(self, user):
        """Deletes all unreviewed reports that the user is involved in."""
        self.unreviewed_reports = [
            (score, report)
            for (score, report) in self.unreviewed_reports
            if report.message.author != user
        ]
        heapq.heapify(self.unreviewed_reports)

    def is_banned(self, user):
        return user in self.banned_users

    def explain_review(
        self,
        message_content: str,
        adversarial: bool,
        action: Literal["suspend", "ban"],
        user,
    ):
        """Explains why action against the user has been taken."""
        ban_msg = "Refer to the linked Community Guidelines for more information."
        if action == "suspend":
            ban_msg = (
                "After "
                + str(self.STRIKE_LIMIT - self.statistics.get_strikes(user.id))
                + " suspension(s) any further violations will get your account banned.\n"
                + ban_msg
            )
        if adversarial:
            return (
                "You have violated our Community Guidelines by targeting a user with wrong reports.\n"
                + f"We do not tolerate this behavior, so we were forced to {action} your account.\n"
                + ban_msg
            )
        return (
            "Your recent messages have violated our Community Guidelines:\n"
            + f"```{message_content}```"
            + f"We do not tolerate this behavior, so we were forced to {action} your account.\n"
            + ban_msg
        )

    async def ban_user(self, user, message_content: str, adversarial: bool):
        # Explain violations and ban user
        embed = discord.Embed(
            title="Your account has been banned!",
            description=self.explain_review(message_content, adversarial, "ban", user),
            color=discord.Color.red(),
            url="https://discord.com/guidelines",
        )
        embed.set_author(name="Community Moderators")
        await user.send(embed=embed)
        self.banned_users.add(user)
        # Remove associated reports and messages
        await self.delete_associated_reports(user)
        await self.delete_messages(user)

    async def suspend_user(self, user, message_content: str, adversarial: bool):
        # Warn the user with explanation and suspend for 7 days
        embed = discord.Embed(
            title="Your account has been suspended for 7 days!",
            description=self.explain_review(
                message_content, adversarial, "suspend", user
            ),
            color=discord.Color.orange(),
            url="https://discord.com/guidelines",
        )
        embed.set_author(name="Community Moderators")
        await user.send(embed=embed)

    async def clean_up_review(self):
        if self.cur_review is None:
            return

        if self.cur_review.review_canceled() and self.cur_review.report_popped():
            # We need to put back the popped report
            self.push_report(self.cur_review.score, self.cur_review.report)
            self.cur_review = None
            return

        if self.cur_review.review_complete():
            embed = discord.Embed(
                title="Review completed!",
                description=f"Thank you for reviewing this report. Necessary actions have been taken.\nThere are now {len(self.unreviewed_reports)} reports outstanding.",
                color=discord.Color.green(),
            )
            await self.mod_channel.send(embed=embed)
            self.cur_review = None

    async def notify_reporter(self, user):
        # Notifies the reporter if the user they reported was punished
        if user != self.user:
            embed = discord.Embed(
                title="Instant Feedback Report",
                description=f"Your recent report was reviewed by our moderation team and the user in question has been issued a penalty. We take every report seriously and value your efforts towards keeping our community accountable.",
                color=discord.Color.green(),
            )
            embed.set_author(name="Community Moderators")
            await user.send(embed=embed)


client = ModBot()
client.run(discord_token)
