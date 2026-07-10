from rest_framework import serializers
from apps.core.common.models import (
    SystemLanguage, SystemTax, SystemDocumentType,
    SystemCurrency, SystemDateFormat, SystemTimeFormat,
    Department, Shift
)

class SystemLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemLanguage
        fields = '__all__'

class SystemTaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemTax
        fields = '__all__'

class SystemDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemDocumentType
        fields = '__all__'

class SystemCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemCurrency
        fields = '__all__'

class SystemDateFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemDateFormat
        fields = '__all__'

class SystemTimeFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemTimeFormat
        fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'
