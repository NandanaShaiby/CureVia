from openai import OpenAI
from django.conf import settings

# Create OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def detect_intent(user_message):
    """
    Detects the intent of the user message.
    Returns one of the predefined intents or 'unknown'.
    """

    prompt = f"""
You are an intent classifier for an online medical store chatbot.

Allowed intents:
1. upload_prescription
2. delivery_time
3. order_tracking
4. payment
5. pharmacy_assignment
6. greetings(Triggered by: hi, hello, hai, hey, good morning, good afternoon, good evening, good night)

User message:
"{user_message}"

Reply with ONLY the intent name.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You only classify intent. Do not answer user questions."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    intent = response.choices[0].message.content.strip().lower()

    allowed_intents = [
        "upload_prescription",
        "delivery_time",
        "order_tracking",
        "payment",
        "pharmacy_assignment",
        "greetings",
    ]

    if intent not in allowed_intents:
        return "unknown"

    return intent
