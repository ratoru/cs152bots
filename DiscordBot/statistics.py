from collections import defaultdict
import random


class APIStatistics:
    def __init__(self) -> None:
        self.total_reports = 0
        self.successful_reports = 0

    def average_success_rate(self) -> float:
        if self.total_reports == 0:
            return 0
        return round(self.successful_reports / self.total_reports * 100, 2)


class UserStatistics:
    """Keeps track of the statistics for one user."""

    def __init__(self) -> None:
        self.strikes = 0  # Number of strikes against the user
        self.reports_against = 0  # How many times the user has been reported
        self.reports_authored = 0  # How many total reports the user has submitted
        self.successful_reports = 0  # How many reports by user are successful
        self.sentiment_total = 0  # Sum of all sentiment scores of the user
        self.num_messages_sent = 0  # Total number of messages sent by the user

    def average_sentiment_score(self) -> float:
        """Returns the average sentiment score of all the messages the user has sent."""
        if self.num_messages_sent == 0:
            return 0
        return round(self.sentiment_total / self.num_messages_sent * 100, 2)

    def average_report_accuracy(self) -> float:
        """Returns the average report accuracy of the user."""
        if self.reports_authored == 0:
            return 0
        return round(self.successful_reports / self.reports_authored * 100, 2)


class Statistics:
    """Keeps track of all statistics needed for the bot."""

    PERCENTAGE_RANGE = 5  # how fine grained the api statistics are

    def __init__(self):
        # TODO: load dict from SQLite
        self.user_statistics = defaultdict(UserStatistics)
        self.api_statistics = defaultdict(APIStatistics)

    # -------- User Statistics --------
    def add_and_check_strike(self, user_id: int, limit: int) -> bool:
        """Adds a strike to the user and returns whether the user has more strikes than the limit."""
        self.user_statistics[user_id].strikes += 1
        return self.user_statistics[user_id].strikes >= limit

    def get_strikes(self, user_id) -> int:
        return self.user_statistics[user_id].strikes

    def get_reports_against(self, user_id: int) -> int:
        return self.user_statistics[user_id].reports_against

    def get_average_sentiment_score(self, user_id: int) -> float:
        return self.user_statistics[user_id].average_sentiment_score()

    def get_average_report_accuracy(self, user_id: int) -> float:
        return self.user_statistics[user_id].average_report_accuracy()

    def increment_reports_against(self, user_id: int):
        self.user_statistics[user_id].reports_against += 1

    def increment_reports_sent(self, user_id: int):
        self.user_statistics[user_id].reports_authored += 1

    def increment_successful_reports(self, user_id: int):
        self.user_statistics[user_id].successful_reports += 1

    def add_sentiment(self, user_id: int, score: float):
        self.user_statistics[user_id].sentiment_total += score
        self.user_statistics[user_id].num_messages_sent += 1

    # -------- API Statistics --------
    def add_report(self, score: float, successful: bool):
        """Adds a (successful) report to the statistics of the API."""
        # Convert score into next multiple of PERCENT_RANGE
        rounded_score = (
            (round(score * 100) // self.PERCENTAGE_RANGE) + 1
        ) * self.PERCENTAGE_RANGE
        self.api_statistics[rounded_score].total_reports += 1
        if successful:
            self.api_statistics[rounded_score].successful_reports += 1

    def api_statistics_overview(self) -> str:
        overview = "How often do sentiment scores in the following ranges lead to succesful reports?\n```"
        for i in range(100 // self.PERCENTAGE_RANGE):
            upper_bound = (i + 1) * self.PERCENTAGE_RANGE
            success_rate = self.api_statistics[upper_bound].average_success_rate()
            overview += "\n{:>2d}-{:>3d}%:".format(
                i * self.PERCENTAGE_RANGE, upper_bound
            )
            overview += "{:>6s}".format(
                f"{self.api_statistics[upper_bound].successful_reports}/{self.api_statistics[upper_bound].total_reports}"
            )
            overview += "   " + "∎" * (int(success_rate) // 10)
        overview += "\n```"
        return overview


if __name__ == "__main__":
    stats = Statistics()
    for i in range(100):
        stats.add_report(random.random(), random.choice([True, False]))
    print(stats.api_statistics_overview())
