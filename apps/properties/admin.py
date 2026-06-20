from django.contrib import admin
from apps.properties.models import PropertyConfiguration, PropertyContact

@admin.register(PropertyConfiguration)
class PropertyConfigurationAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'timezone', 'currency', 'language')

@admin.register(PropertyContact)
class PropertyContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'phone', 'email')
