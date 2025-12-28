from django.urls import path

from messaging.views import MessageAPIView

urlpatterns = [
	path('message/<int:room_id>', MessageAPIView.as_view(), name='message-send'),

]