from django.urls import path

from messaging.views import MessageAPIView, RoomAPIView

urlpatterns = [
	path('message/<int:room_id>', MessageAPIView.as_view(), name='message-send'),
	path('room', RoomAPIView.as_view(), name='message-list'),

]