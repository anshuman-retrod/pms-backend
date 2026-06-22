from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
import base64
import logging

from apps.features.crm.models import (
    GuestProfile, GuestContact, GuestDocument, GuestPreference,
    GuestTag, GuestProfileTag, GuestActivity
)

logger = logging.getLogger(__name__)

class EncryptionHelper:
    @staticmethod
    def encrypt(value):
        if not value:
            return ""
        return base64.b64encode(value.encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt(value):
        if not value:
            return ""
        try:
            return base64.b64decode(value.encode('utf-8')).decode('utf-8')
        except Exception:
            return value


class GuestMergeService:
    @staticmethod
    def resolve_profile(profile):
        seen = {profile.id}
        while profile.master_guest:
            if profile.master_guest_id in seen:
                break
            profile = profile.master_guest
            seen.add(profile.id)
        return profile

    @classmethod
    @transaction.atomic
    def merge_profiles(cls, tenant, master_profile, duplicate_profile, user=None):
        if master_profile.tenant != tenant or duplicate_profile.tenant != tenant:
            raise ValidationError("Both profiles must belong to the resolved tenant context.")
        if master_profile == duplicate_profile:
            raise ValidationError("Cannot merge a profile into itself.")

        # If master_profile is itself merged, resolve to its master
        master_profile = cls.resolve_profile(master_profile)

        # Update duplicate profile fields
        duplicate_profile.master_guest = master_profile
        duplicate_profile.is_active = False
        duplicate_profile.save(update_fields=['master_guest', 'is_active'])

        # Aggregate points & stays
        master_profile.loyalty_points += duplicate_profile.loyalty_points
        master_profile.total_stays += duplicate_profile.total_stays
        master_profile.total_nights += duplicate_profile.total_nights
        
        if duplicate_profile.last_stay_date:
            if not master_profile.last_stay_date or duplicate_profile.last_stay_date > master_profile.last_stay_date:
                master_profile.last_stay_date = duplicate_profile.last_stay_date

        master_profile.save(update_fields=['loyalty_points', 'total_stays', 'total_nights', 'last_stay_date'])

        # Re-link preferences
        for pref in duplicate_profile.preferences.all():
            if not master_profile.preferences.filter(preference_key=pref.preference_key).exists():
                pref.guest = master_profile
                pref.save(update_fields=['guest'])
            else:
                pref.delete()

        # Re-link contacts
        for contact in duplicate_profile.contacts.all():
            contact.is_primary = False
            if not master_profile.contacts.filter(email=contact.email, phone=contact.phone).exists():
                contact.guest = master_profile
                contact.save(update_fields=['guest', 'is_primary'])
            else:
                contact.delete()

        # Re-link documents
        for doc in duplicate_profile.documents.all():
            if not master_profile.documents.filter(document_type=doc.document_type).exists():
                doc.guest = master_profile
                doc.save(update_fields=['guest'])
            else:
                doc.delete()

        # Re-link tags
        for pt in duplicate_profile.profile_tags.all():
            if not master_profile.profile_tags.filter(tag=pt.tag).exists():
                pt.guest = master_profile
                pt.save(update_fields=['guest'])
            else:
                pt.delete()

        # Log CRM Activity
        GuestActivity.objects.create(
            tenant=tenant,
            guest=master_profile,
            activity_type='PROFILE_MERGE',
            description=f"Merged duplicate profile {duplicate_profile.first_name} {duplicate_profile.last_name} ({duplicate_profile.id}) into master profile."
        )

        return master_profile


class LoyaltyService:
    @staticmethod
    def evaluate_tier(points):
        if points >= 10000:
            return 'PLATINUM'
        elif points >= 6000:
            return 'GOLD'
        elif points >= 3000:
            return 'SILVER'
        elif points >= 1000:
            return 'BRONZE'
        return 'STANDARD'

    @classmethod
    def add_points(cls, tenant, profile, points, reason, user=None):
        if profile.tenant != tenant:
            raise ValidationError("Profile must belong to the resolved tenant context.")
        if points < 0:
            raise ValidationError("Points to add must be non-negative.")

        # Work on resolved active profile
        profile = GuestMergeService.resolve_profile(profile)

        profile.loyalty_points += points
        new_tier = cls.evaluate_tier(profile.loyalty_points)
        old_tier = profile.loyalty_tier
        
        update_fields = ['loyalty_points']
        tier_upgraded = False
        if new_tier != old_tier:
            profile.loyalty_tier = new_tier
            update_fields.append('loyalty_tier')
            tier_upgraded = True

        profile.save(update_fields=update_fields)

        # Log Activity
        desc = f"Earned {points} loyalty points for: {reason}."
        if tier_upgraded:
            desc += f" Tier upgraded from {old_tier} to {new_tier}."

        GuestActivity.objects.create(
            tenant=tenant,
            guest=profile,
            activity_type='LOYALTY_EARN',
            description=desc,
            payload={'points_added': points, 'new_tier': new_tier, 'old_tier': old_tier}
        )
        return profile


class DocumentVerificationService:
    @staticmethod
    def verify_document(tenant, document, user=None):
        if document.tenant != tenant:
            raise ValidationError("Document must belong to the resolved tenant context.")
        
        document.is_verified = True
        document.save(update_fields=['is_verified'])

        # Decrypt a portion of document number for logging safety
        decrypted_num = EncryptionHelper.decrypt(document.document_number)
        ending = decrypted_num[-4:] if len(decrypted_num) > 4 else ""

        GuestActivity.objects.create(
            tenant=tenant,
            guest=document.guest,
            activity_type='DOCUMENT_VERIFIED',
            description=f"Verified {document.document_type} ending in ...{ending}."
        )
        return document


class GuestSearchEngine:
    @staticmethod
    def search_guests(tenant, query_str=None, tag_code=None):
        qs = GuestProfile.objects.filter(tenant=tenant, is_active=True)
        if query_str:
            qs = qs.filter(
                Q(first_name__icontains=query_str) |
                Q(last_name__icontains=query_str) |
                Q(contacts__email__icontains=query_str) |
                Q(contacts__phone__icontains=query_str)
            ).distinct()

        if tag_code:
            qs = qs.filter(profile_tags__tag__code=tag_code)
            
        return qs


class TaggingService:
    @staticmethod
    def assign_tag(tenant, profile, tag_code, user=None):
        if profile.tenant != tenant:
            raise ValidationError("Profile must belong to the resolved tenant context.")
        
        # Work on resolved active profile
        profile = GuestMergeService.resolve_profile(profile)

        tag = GuestTag.objects.filter(
            Q(tenant=tenant) | Q(tenant__isnull=True),
            code=tag_code
        ).first()
        
        if not tag:
            raise ValidationError(f"Tag with code '{tag_code}' does not exist.")

        pt, created = GuestProfileTag.objects.get_or_create(
            guest=profile,
            tag=tag
        )
        
        if created:
            GuestActivity.objects.create(
                tenant=tenant,
                guest=profile,
                activity_type='TAG_ASSIGNED',
                description=f"Assigned tag '{tag.name}' ({tag.code}) to profile."
            )
            
        return pt
