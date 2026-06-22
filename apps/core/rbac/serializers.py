from rest_framework import serializers
from apps.core.rbac.models import Permission, Role, RolePermission, UserPropertyRole

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class RolePermissionSerializer(serializers.ModelSerializer):
    permission_code = serializers.CharField(source='permission.code', read_only=True)
    
    class Meta:
        model = RolePermission
        fields = '__all__'

class UserPropertyRoleSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = UserPropertyRole
        fields = '__all__'
