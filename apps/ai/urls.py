from django.urls import path

from .views import ChatHistoryView, ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("chat/history/<uuid:lead_id>/", ChatHistoryView.as_view(), name="chat-history"),
]
