from enum import Enum, auto
import discord
import re
from review_views import ReviewStart


class State(Enum):
    REVIEW_START = auto()
    AWAITING_REPORT = auto()
    IN_VIEW = auto()
    REVIEW_CANCELED = auto()
    REVIEW_COMPLETE = auto()


class Review:
    START_KEYWORD = "review"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client  # the bot
        self.score = -1
        self.report = None

    async def handle_message(self, message):
        """
        This functions handles the manual review process.
        Much of the flow is handled via views.
        """

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REVIEW_CANCELED
            return ["Review cancelled."]

        if self.state == State.REVIEW_START:
            if not self.client.unreviewed_reports:
                self.state = State.REVIEW_CANCELED
                return ["There are no reviews to review."]
            reply = "Thank you for starting the review process. "
            reply += "Say `help` at any time for more information.\n\n"
            self.state = State.IN_VIEW
            return [(reply, ReviewStart(self))]

        if self.state == State.IN_VIEW:
            # If there is a view, the view should be interacted with.
            return [
                "Sorry, you are in the middle of a review process.\nContinue by selecting an option above or stop by typing `cancel`."
            ]

        return []

    def review_canceled(self):
        return self.state == State.REVIEW_CANCELED

    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE

    def report_popped(self):
        return self.report is not None

    async def finish_review(self):
        """Finishes the report by setting the type to complete and calling the client's clean up funciton."""
        self.state = State.REVIEW_COMPLETE
        await self.client.clean_up_review()

    # State setters and getters
    def set_report(self, report):
        self.report = report

    def set_score(self, score):
        self.score = score
