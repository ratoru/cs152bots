from collections import defaultdict


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

    def __init__(self):
        # TODO: load dict from SQLite
        self.user_statistics = defaultdict(UserStatistics)

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


# if __name__ == "__main__":
#     stats = Statistics()
#     for i in range(4):
#         print(stats.add_strike(0, 3))
#         print(stats.get_strikes(0))
# On a bot basis:
# - I was thinking of splitting probabilities into ranges (e.g. every 5% is an entry in a dict) and keeping track of how successful these reports are
