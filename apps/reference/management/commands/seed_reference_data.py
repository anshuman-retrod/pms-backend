from django.core.management.base import BaseCommand
from apps.reference.models import Country, Nationality, Language, Currency, DocumentType, ReservationSource

class Command(BaseCommand):
    help = 'Seeds Global Reference Data including ISO countries, currencies, languages, nationalities, document types, and reservation sources.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding global reference data...")

        # 1. ISO Currencies
        currencies = [
            {"code": "USD", "name": "US Dollar", "symbol": "$"},
            {"code": "INR", "name": "Indian Rupee", "symbol": "₹"},
            {"code": "EUR", "name": "Euro", "symbol": "€"},
            {"code": "GBP", "name": "British Pound", "symbol": "£"},
            {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$"},
            {"code": "AUD", "name": "Australian Dollar", "symbol": "A$"},
            {"code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
            {"code": "AED", "name": "UAE Dirham", "symbol": "د.إ"},
            {"code": "SGD", "name": "Singapore Dollar", "symbol": "S$"},
            {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF"},
            {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥"},
            {"code": "NZD", "name": "New Zealand Dollar", "symbol": "NZ$"},
        ]
        for curr in currencies:
            Currency.objects.update_or_create(code=curr["code"], defaults=curr)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(currencies)} currencies."))

        # 2. ISO Countries
        countries = [
            {"code": "US", "name": "United States", "phone_code": "+1"},
            {"code": "IN", "name": "India", "phone_code": "+91"},
            {"code": "GB", "name": "United Kingdom", "phone_code": "+44"},
            {"code": "CA", "name": "Canada", "phone_code": "+1"},
            {"code": "DE", "name": "Germany", "phone_code": "+49"},
            {"code": "FR", "name": "France", "phone_code": "+33"},
            {"code": "AU", "name": "Australia", "phone_code": "+61"},
            {"code": "JP", "name": "Japan", "phone_code": "+81"},
            {"code": "AE", "name": "United Arab Emirates", "phone_code": "+971"},
            {"code": "SG", "name": "Singapore", "phone_code": "+65"},
            {"code": "CH", "name": "Switzerland", "phone_code": "+41"},
            {"code": "CN", "name": "China", "phone_code": "+86"},
            {"code": "NZ", "name": "New Zealand", "phone_code": "+64"},
        ]
        for country in countries:
            Country.objects.update_or_create(code=country["code"], defaults=country)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(countries)} countries."))

        # 3. Common Languages
        languages = [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "hi", "name": "Hindi"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ar", "name": "Arabic"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "it", "name": "Italian"},
            {"code": "ru", "name": "Russian"},
        ]
        for lang in languages:
            Language.objects.update_or_create(code=lang["code"], defaults=lang)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(languages)} languages."))

        # 4. Nationalities
        nationalities = [
            {"code": "american", "name": "American"},
            {"code": "indian", "name": "Indian"},
            {"code": "british", "name": "British"},
            {"code": "canadian", "name": "Canadian"},
            {"code": "german", "name": "German"},
            {"code": "french", "name": "French"},
            {"code": "australian", "name": "Australian"},
            {"code": "japanese", "name": "Japanese"},
            {"code": "emirati", "name": "Emirati"},
            {"code": "singaporean", "name": "Singaporean"},
            {"code": "swiss", "name": "Swiss"},
            {"code": "chinese", "name": "Chinese"},
            {"code": "kiwi", "name": "New Zealander"},
        ]
        for nat in nationalities:
            Nationality.objects.update_or_create(code=nat["code"], defaults=nat)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(nationalities)} nationalities."))

        # 5. Global Document Types
        doc_types = [
            {"code": "passport", "name": "Passport"},
            {"code": "national_id", "name": "National ID Card"},
            {"code": "driving_license", "name": "Driving License"},
            {"code": "visa", "name": "Visa"},
            {"code": "voter_id", "name": "Voter ID Card"},
            {"code": "pan_card", "name": "PAN Card"},
        ]
        for doc in doc_types:
            DocumentType.objects.update_or_create(code=doc["code"], defaults=doc)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(doc_types)} document types."))

        # 6. Common Reservation Sources
        sources = [
            {"code": "direct", "name": "Direct / Walk-In"},
            {"code": "website", "name": "Brand Website"},
            {"code": "booking_com", "name": "Booking.com"},
            {"code": "expedia", "name": "Expedia"},
            {"code": "agoda", "name": "Agoda"},
            {"code": "airbnb", "name": "Airbnb"},
            {"code": "corporate", "name": "Corporate Client"},
            {"code": "travel_agent", "name": "Offline Travel Agent"},
            {"code": "email_phone", "name": "Email / Phone Inquiry"},
        ]
        for src in sources:
            ReservationSource.objects.update_or_create(code=src["code"], defaults=src)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(sources)} reservation sources."))

        self.stdout.write(self.style.SUCCESS("Global reference data seeding completed!"))
