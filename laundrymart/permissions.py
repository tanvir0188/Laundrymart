from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
	def has_permission(self, request, view):
		return bool(request.user and request.user.is_staff and request.user.is_superuser)

class IsStaff(BasePermission):
	def has_permission(self, request, view):
		return bool(request.user and request.user.is_staff)
		#return bool(request.user and request.user.is_staff and request.user.approved_by_admin)

class IsCustomer(BasePermission):
	def has_permission(self, request, view):
		return bool(request.user and request.user.is_authenticated and not request.user.is_staff)