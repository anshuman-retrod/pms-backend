from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import InventoryUnit, InventoryUnitType, InventoryUnitCategory
from apps.features.housekeeping.models import (
    CleaningTask, RoomInspection, DeepCleaningSchedule, TurndownService,
    MinibarInventory, MinibarRefill, AmenityInventory, HousekeepingInventory
)

User = get_user_model()

class HousekeepingModelsTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Hotel Biraj Group", subdomain="biraj")
        self.property = Property.objects.create(tenant=self.tenant, name="Main Wing")
        
        self.staff = User.objects.create_user(
            username="hksuff",
            email="hk@biraj.com",
            password="testpassword"
        )
        
        self.category = InventoryUnitCategory.objects.create(
            tenant=self.tenant,
            code="ROOM",
            name="Room"
        )
        self.unit_type = InventoryUnitType.objects.create(
            tenant=self.tenant,
            property=self.property,
            category=self.category,
            code="STD",
            name="Standard Room"
        )
        self.room = InventoryUnit.objects.create(
            tenant=self.tenant,
            property=self.property,
            inventory_unit_type=self.unit_type,
            name="101",
            floor=1
        )

    def test_cleaning_task_creation(self):
        task = CleaningTask.objects.create(
            tenant=self.tenant,
            room=self.room,
            assigned_staff=self.staff,
            status="PENDING",
            priority="RUSH"
        )
        self.assertEqual(task.status, "PENDING")
        self.assertEqual(task.priority, "RUSH")

    def test_room_inspection_creation(self):
        insp = RoomInspection.objects.create(
            tenant=self.tenant,
            room=self.room,
            inspector=self.staff,
            score=95,
            result="PASSED"
        )
        self.assertEqual(insp.score, 95)
        self.assertEqual(insp.result, "PASSED")

    def test_deep_cleaning_schedule(self):
        sched = DeepCleaningSchedule.objects.create(
            tenant=self.tenant,
            room=self.room,
            scheduled_date=timezone.now().date(),
            status="SCHEDULED"
        )
        self.assertEqual(sched.status, "SCHEDULED")

    def test_turndown_service(self):
        td = TurndownService.objects.create(
            tenant=self.tenant,
            room=self.room,
            status="PENDING"
        )
        self.assertEqual(td.status, "PENDING")

    def test_minibar_inventory_and_refill(self):
        item = MinibarInventory.objects.create(
            tenant=self.tenant,
            room=self.room,
            item_name="Cola",
            quantity=4,
            price=Decimal("5.00")
        )
        self.assertEqual(item.quantity, 4)

        refill = MinibarRefill.objects.create(
            tenant=self.tenant,
            room=self.room,
            item_name="Cola",
            quantity_consumed=2,
            quantity_refilled=2
        )
        self.assertEqual(refill.quantity_consumed, 2)

    def test_amenity_inventory(self):
        amenity = AmenityInventory.objects.create(
            tenant=self.tenant,
            room=self.room,
            amenity_name="Shampoo",
            quantity=5
        )
        self.assertEqual(amenity.quantity, 5)

    def test_housekeeping_supplies(self):
        supply = HousekeepingInventory.objects.create(
            tenant=self.tenant,
            property=self.property,
            supply_name="Glass Cleaner",
            total_qty=20,
            reorder_level=5
        )
        self.assertEqual(supply.total_qty, 20)
