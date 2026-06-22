from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.subscriptions.models import TenantSubscription, TenantProduct, TenantProductLicense

class Command(BaseCommand):
    help = 'Auto-expires subscriptions, active products, and licenses when their validity period passes.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        self.stdout.write(f"Checking for expired subscriptions as of today: {today}...")

        # Find active subscriptions that have passed their end date
        expired_subs = TenantSubscription.objects.filter(
            status='ACTIVE',
            end_date__lt=today
        )

        sub_count = expired_subs.count()
        if sub_count == 0:
            self.stdout.write(self.style.SUCCESS("No subscriptions expired today."))
            return

        for sub in expired_subs:
            # Update subscription status to EXPIRED
            sub.status = 'EXPIRED'
            sub.save()

            # Automatically deactivate/expire associated Tenant Products
            associated_products = TenantProduct.objects.filter(
                tenant=sub.tenant,
                tenant_subscription=sub,
                status='ACTIVE'
            )
            for prod in associated_products:
                prod.status = 'EXPIRED'
                prod.save()

                # Automatically expire licenses
                TenantProductLicense.objects.filter(
                    tenant_product=prod,
                    status='ACTIVE'
                ).update(status='EXPIRED')

            self.stdout.write(f"Expired subscription {sub.id} for tenant {sub.tenant.name}.")

        self.stdout.write(self.style.SUCCESS(f"Successfully processed and expired {sub_count} subscriptions and their associated products/licenses."))
