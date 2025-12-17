from .openai_intent import detect_intent
from .utils import FAQ_RESPONSES


def get_chatbot_response(user_message):
    """
    Main chatbot logic:
    1. Detect intent using OpenAI
    2. Return predefined FAQ response
    """

    intent = detect_intent(user_message)
    response = FAQ_RESPONSES.get(intent, FAQ_RESPONSES["unknown"])

    return response
