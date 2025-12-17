from django.urls import path
from .views import *

urlpatterns = [
    path("chat/", chatbot_api, name="chatbot_api"),
    path("ui/", chatbot_page, name="chatbot_ui"),
]
