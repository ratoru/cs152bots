from googleapiclient import discovery
from unidecode import unidecode
import json
import os


# There should be a file called 'tokens.json' inside the same folder as this file
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    perspective_token = tokens["perspective-api-key"]


# These are the attributes that will be checked by the API.
# This is the format the API expects.
requestedAttributes = {
    "TOXICITY": {},
    "SEVERE_TOXICITY": {},
    "IDENTITY_ATTACK": {},
    "INSULT": {},
    "THREAT": {},
}


def analyze_text(text: str) -> float:
    """Given a piece of text, returns the probability the text is harassment according to the Perspective API.

    Args:
        text (str): the text to analyze

    Returns:
        float: the probability the string is harassment
    """
    # Convert Unicode characters to ascii characters.
    # This aims to prevent adversarial unicode texts.
    ascii_text = unidecode(text)

    # Open socket for request
    with discovery.build(
        "commentanalyzer",
        "v1alpha1",
        developerKey=perspective_token,
        discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
        static_discovery=False,
    ) as client:
        analyze_request = {
            "comment": {"text": ascii_text},
            "requestedAttributes": requestedAttributes,
        }
        response = client.comments().analyze(body=analyze_request).execute()
        return analyze_scores(response)


def analyze_scores(response) -> float:
    """Given a response from the Perspective API returns the highest probability.

    Args:
        response: object returned by the Perspective API
    Returns:
        highest probability in the response
    """
    probability = 0
    for attribute in requestedAttributes:
        attribute_probability = response["attributeScores"][attribute]["summaryScore"][
            "value"
        ]
        if attribute_probability > probability:
            probability = attribute_probability
    return probability


if __name__ == "__main__":
    analyze_text("this is a test, asshole!")
