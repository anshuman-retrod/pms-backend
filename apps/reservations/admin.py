from django.contrib import admin
from apps.reservations.models import (
    CorporateAccount, GroupBlock, Reservation, ReservationInventory,
    ReservationRateSnapshot, ReservationGuest, ReservationEvent
)

@admin.register(CorporateAccount)
class CorporateAccountAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'negotiated_rate_code', 'credit_limit', 'open_invoices_count', 'is_active')
    search_fields = ('company_name', 'negotiated_rate_code')
    list_filter = ('is_active',)


@admin.register(GroupBlock)
class GroupBlockAdmin(admin.ModelAdmin):
    list_display = ('name', 'block_type', 'status', 'cutoff_date', 'total_rooms', 'pickup_rooms')
    search_fields = ('name',)
    list_filter = ('status', 'block_type')


class ReservationInventoryInline(admin.TabularInline):
    model = ReservationInventory
    extra = 0


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('confirmation_number', 'primary_guest', 'status', 'arrival_date', 'departure_date', 'total_amount')
    search_fields = ('confirmation_number', 'booking_reference')
    list_filter = ('status', 'reservation_type', 'market_segment')
    inlines = [ReservationInventoryInline]


@admin.register(ReservationInventory)
class ReservationInventoryAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'inventory_unit', 'inventory_unit_type', 'check_in_date', 'check_out_date', 'status')
    list_filter = ('status',)


@admin.register(ReservationRateSnapshot)
class ReservationRateSnapshotAdmin(admin.ModelAdmin):
    list_display = ('reservation_inventory', 'date', 'amount_charged', 'rate_plan')


@admin.register(ReservationGuest)
class ReservationGuestAdmin(admin.ModelAdmin):
    list_display = ('reservation_inventory', 'guest', 'is_primary', 'is_checked_in')
    list_filter = ('is_checked_in',)


@admin.register(ReservationEvent)
class ReservationEventAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'event_type', 'timestamp', 'actor_user')
    readonly_fields = ('tenant', 'reservation', 'timestamp', 'event_type', 'description', 'actor_user', 'payload_diff')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
