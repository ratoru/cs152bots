# CS 152 - Trust and Safety Engineering

Group 34.

## Discord Bot Framework Code

This is the base framework for students to complete Milestone 2 of the CS 152 final project. Please follow the instructions you were provided to fork this repository into your own repository and make all of your additions there.

## Notable Things

- Multiple languages supported
- Detailed statistics on users
- Detailed statistics on the predictive power of the API
- Intuitive report and review flows using `discord.ui`
- Priority queue of reports to handle reports by urgency.
- Allow moderators to review oldest report, so no report starves.
- Reduce friction while reporting as much as possible while still allowing for detailed reports.
- Strike system with temporary suspensions.
- User feedback during reports and if report successful.
- Safeguards:
  - Converts unicode characters to ascii before evaluating the message.
  - Cannot report banned users.
  - All reports against a user get deleted once they're banned.
