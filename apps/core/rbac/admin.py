from django.contrib import admin
from apps.core.rbac.models import Permission, Role, RolePermission, UserPropertyRole

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'category')
    search_fields = ('code', 'category')
    list_filter = ('category',)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'tenant')
    search_fields = ('name', 'code')
    list_filter = ('tenant',)

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission')
    list_filter = ('role',)

@admin.register(UserPropertyRole)
class UserPropertyRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'role', 'tenant')
    list_filter = ('tenant', 'property', 'role')
