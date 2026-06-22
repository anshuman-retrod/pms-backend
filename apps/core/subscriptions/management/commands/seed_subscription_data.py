from django.core.management.base import BaseCommand
from apps.core.subscriptions.models import Product, SubscriptionPlan, SubscriptionEntitlement, SubscriptionPlanProduct

class Command(BaseCommand):
    help = 'Seeds subscription plans, products, and feature entitlements.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding products...")

        # 1. Products
        products = [
            {"code": "PMS", "name": "Property Management System", "description": "Core PMS module"},
            {"code": "POS", "name": "Point of Sale", "description": "F&B and Retail billing"},
            {"code": "CRM", "name": "Guest CRM", "description": "Loyalty and guest profile tracking"},
            {"code": "CHANNEL_MANAGER", "name": "Channel Manager Link", "description": "OTA distribution sync"},
            {"code": "HOUSEKEEPING", "name": "Housekeeping Module", "description": "Mobile app and task logs"},
        ]
        prod_objs = {}
        for p in products:
            obj, _ = Product.objects.update_or_create(code=p["code"], defaults=p)
            prod_objs[p["code"]] = obj
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(products)} products."))

        # 2. Subscription Plans
        plans = [
            {"name": "Lite", "billing_cycle": "MONTHLY", "price": 49.00, "currency": "USD"},
            {"name": "Standard", "billing_cycle": "MONTHLY", "price": 99.00, "currency": "USD"},
            {"name": "Enterprise", "billing_cycle": "MONTHLY", "price": 249.00, "currency": "USD"},
        ]
        plan_objs = {}
        for plan in plans:
            obj, _ = SubscriptionPlan.objects.update_or_create(name=plan["name"], defaults=plan)
            plan_objs[plan["name"]] = obj
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(plans)} plans."))

        # 3. Associate Products & Entitlements
        # Lite: PMS, HOUSEKEEPING
        lite = plan_objs["Lite"]
        SubscriptionPlanProduct.objects.update_or_create(plan=lite, product=prod_objs["PMS"])
        SubscriptionPlanProduct.objects.update_or_create(plan=lite, product=prod_objs["HOUSEKEEPING"])
        SubscriptionEntitlement.objects.update_or_create(plan=lite, feature_code="ROOM_LIMIT", defaults={"limit_type": "NUMERIC", "limit_value": 25})
        SubscriptionEntitlement.objects.update_or_create(plan=lite, feature_code="CRM_ACCESS", defaults={"limit_type": "BOOLEAN", "limit_value": False})

        # Standard: PMS, HOUSEKEEPING, POS, CRM
        std = plan_objs["Standard"]
        SubscriptionPlanProduct.objects.update_or_create(plan=std, product=prod_objs["PMS"])
        SubscriptionPlanProduct.objects.update_or_create(plan=std, product=prod_objs["HOUSEKEEPING"])
        SubscriptionPlanProduct.objects.update_or_create(plan=std, product=prod_objs["POS"])
        SubscriptionPlanProduct.objects.update_or_create(plan=std, product=prod_objs["CRM"])
        SubscriptionEntitlement.objects.update_or_create(plan=std, feature_code="ROOM_LIMIT", defaults={"limit_type": "NUMERIC", "limit_value": 100})
        SubscriptionEntitlement.objects.update_or_create(plan=std, feature_code="CRM_ACCESS", defaults={"limit_type": "BOOLEAN", "limit_value": True})

        # Enterprise: ALL products
        ent = plan_objs["Enterprise"]
        for p_code, p_obj in prod_objs.items():
            SubscriptionPlanProduct.objects.update_or_create(plan=ent, product=p_obj)
        SubscriptionEntitlement.objects.update_or_create(plan=ent, feature_code="ROOM_LIMIT", defaults={"limit_type": "NUMERIC", "limit_value": 9999})
        SubscriptionEntitlement.objects.update_or_create(plan=ent, feature_code="CRM_ACCESS", defaults={"limit_type": "BOOLEAN", "limit_value": True})

        self.stdout.write(self.style.SUCCESS("Subscription & Entitlement seeding completed!"))
