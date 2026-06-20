from django.contrib import admin
from apps.crm.models import (
    GuestProfile, GuestContact, GuestDocument, GuestPreference,
    GuestTag, GuestProfileTag, GuestActivity
)

@admin.register(GuestProfile)
class GuestProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'guest_type', 'loyalty_tier', 'loyalty_points', 'is_active', 'tenant')
    list_filter = ('guest_type', 'loyalty_tier', 'is_active', 'tenant')
    search_fields = ('first_name', 'last_name')

@admin.register(GuestContact)
class GuestContactAdmin(admin.ModelAdmin):
    list_display = ('guest', 'email', 'phone', 'is_primary', 'tenant')
    list_filter = ('is_primary', 'tenant')
    search_fields = ('guest__first_name', 'guest__last_name', 'email', 'phone')

@admin.register(GuestDocument)
class GuestDocumentAdmin(admin.ModelAdmin):
    list_display = ('guest', 'document_type', 'expiry_date', 'is_verified', 'tenant')
    list_filter = ('document_type', 'is_verified', 'tenant')
    search_fields = ('guest__first_name', 'guest__last_name')

@admin.register(GuestPreference)
class GuestPreferenceAdmin(admin.ModelAdmin):
    list_display = ('guest', 'preference_category', 'preference_key', 'preference_value')
    list_filter = ('preference_category',)
    search_fields = ('guest__first_name', 'guest__last_name', 'preference_key')

@admin.register(GuestTag)
class GuestTagAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('code', 'name')

@admin.register(GuestProfileTag)
class GuestProfileTagAdmin(admin.ModelAdmin):
    list_display = ('guest', 'tag')

@admin.register(GuestActivity)
class GuestActivityAdmin(admin.ModelAdmin):
    list_display = ('guest', 'activity_type', 'timestamp', 'tenant')
    list_filter = ('activity_type', 'tenant')
    search_fields = ('guest__first_name', 'guest__last_name', 'description')
