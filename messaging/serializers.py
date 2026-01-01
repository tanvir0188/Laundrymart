from rest_framework import serializers

from messaging.models import Message, Room


class MessageSerializer(serializers.ModelSerializer):
	user = serializers.StringRelatedField(read_only=True)
	sender=serializers.SerializerMethodField()

	class Meta:
		model = Message
		fields = ['id', 'text','user','sender', 'room','file', 'created_at', 'updated_at', 'seen']
		read_only_fields = ['created_at', 'updated_at', 'seen', 'room']

	def get_sender(self,obj):
		return obj.user.id

class RoomSerializer(serializers.ModelSerializer):
	other_user=serializers.SerializerMethodField()
	other_user_image=serializers.SerializerMethodField()
	unseen_count=serializers.SerializerMethodField()
	last_message=serializers.SerializerMethodField()
	order_id=serializers.CharField(source='order.uuid',read_only=True)
	class Meta:
		model = Room
		fields = ['id','order', 'order_id', 'name', 'participants', 'created_at','other_user', 'other_user_image','unseen_count','updated_at','last_message']
		read_only_fields = ['participants','name', 'created_at', 'updated_at', 'other_user']

	def get_other_user(self, obj):
		request = self.context.get('request')
		if not request or not hasattr(request, "user"):
			return None

		user = request.user
		participants = obj.participants.all()
		other = participants.exclude(id=user.id).first()
		return other.full_name if other else None
	def get_other_user_image(self, obj):
		request = self.context.get('request')
		if not request or not hasattr(request, "user"):
			return None

		user = request.user
		participants = obj.participants.all()
		other = participants.exclude(id=user.id).first()
		if other and other.image:
			return request.build_absolute_uri(other.image.url)
		return None

	def get_last_message(self, obj):
		last_message = obj.messages.order_by('-created_at').first()  # get the latest message
		if last_message:
			return last_message.text or last_message.file.url
		return None


	def get_unseen_count(self, obj):
		request = self.context.get('request')
		if not request or not hasattr(request, "user"):
			return None
		user = request.user
		participants = obj.participants.all()
		other = participants.exclude(id=user.id).first()
		unseen_messages=Message.objects.filter(room=obj,user=other, seen=False).count()
		return unseen_messages
