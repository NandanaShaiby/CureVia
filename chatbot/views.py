from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render

from .services import get_chatbot_response


@csrf_exempt
def chatbot_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")

        reply = get_chatbot_response(user_message)

        return JsonResponse({"reply": reply})

    return JsonResponse({"error": "Invalid request method"}, status=400)

def chatbot_page(request):
    return render(request, "chatbot.html")
