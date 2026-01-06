from django.urls import path

from messaging.views import MessageAPIView, RoomAPIView, VendorNotificationAPIView, VendorNotificationModifyAPIView

urlpatterns = [
	path('message/<int:room_id>', MessageAPIView.as_view(), name='message-send'),
	path('room', RoomAPIView.as_view(), name='message-list'),
	path('vendor-notifications', VendorNotificationAPIView.as_view(), name='vendor-notifications'),
	path('vendor-notifications/<int:notification_id>/<str:action>',VendorNotificationModifyAPIView.as_view(),name='vendor-notification-modify-action'),

]