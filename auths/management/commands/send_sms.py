from django.core.management.base import BaseCommand

from auths.sms_service import get_sms_service


class Command(BaseCommand):
    help = "Send SMS via Benter Group"

    def add_arguments(self, parser):
        parser.add_argument("phone", type=str, nargs="?", help="Phone number")
        parser.add_argument("message", type=str, nargs="?", help="Message to send")
        parser.add_argument("--balance", action="store_true", help="Check SMS balance")
        parser.add_argument("--test", type=str, help="Send test message to phone number")

    def handle(self, *args, **options):
        sms = get_sms_service()

        if options["balance"]:
            balance = sms.get_balance()
            self.stdout.write(self.style.SUCCESS(f"SMS Balance: {balance}"))
            return

        if options["test"]:
            phone = options["test"]
            message = "Test SMS from Shabiby Cargo System. If you receive this, SMS integration is working!"

            self.stdout.write(f"Sending test SMS to {phone}...")
            self.stdout.write(f"Provider: {sms.provider_name}")
            self.stdout.write(f"Enabled: {sms.enabled}")
            result = sms.send_sms(phone, message)

            if result.get("success"):
                self.stdout.write(self.style.SUCCESS("Test SMS sent successfully!"))
                self.stdout.write(f"Response: {result.get('response', {})}")
            else:
                self.stdout.write(self.style.ERROR(f"Failed: {result.get('error', result.get('response', {}))}"))
                if "status_code" in result:
                    self.stdout.write(f"Status Code: {result['status_code']}")
            return

        if not options["phone"] or not options["message"]:
            self.stdout.write(self.style.ERROR("Error: phone and message are required"))
            self.stdout.write("Usage: python manage.py send_sms <phone> <message>")
            self.stdout.write("       python manage.py send_sms --balance")
            self.stdout.write("       python manage.py send_sms --test <phone>")
            return

        phone = options["phone"]
        message = options["message"]

        self.stdout.write(f"Sending SMS to {phone}...")
        result = sms.send_sms(phone, message)

        if result.get("success"):
            self.stdout.write(self.style.SUCCESS("SMS sent successfully!"))
            self.stdout.write(f"Status Code: {result.get('status_code')}")
            self.stdout.write(f"Response: {result.get('response', {})}")
        else:
            self.stdout.write(self.style.ERROR(f"Failed: {result.get('error', result.get('response', {}))}"))
            if "status_code" in result:
                self.stdout.write(f"Status Code: {result['status_code']}")
