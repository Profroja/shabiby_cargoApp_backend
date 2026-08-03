"""
SMS Integration Service
Supports Benter Group (can be extended for other providers)
"""
import logging

import requests

logger = logging.getLogger(__name__)


class BenterSMSProvider:
    """Benter Group SMS Provider"""

    def __init__(self, api_key, client_id, sender, url, balance_url):
        self.api_key = api_key
        self.client_id = client_id
        self.sender = sender
        self.url = url
        self.balance_url = balance_url

    def send(self, recipient, message):
        """Send SMS via Benter Group"""
        try:
            payload = {
                "SenderId": self.sender,
                "IsUnicode": True,
                "IsFlash": False,
                "ApiKey": self.api_key,
                "ClientId": self.client_id,
                "MessageParameters": [{"Number": recipient, "Text": message}],
            }

            logger.info(f"(BENTER) Sending SMS to {recipient}")

            response = requests.post(
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.json() if response.content else {},
            }

        except Exception as e:
            logger.error(f"(BENTER) Failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_balance(self):
        """Check SMS balance"""
        try:
            response = requests.get(
                self.balance_url,
                params={"ApiKey": self.api_key, "ClientId": self.client_id},
                timeout=5,
            )

            if response.status_code == 200:
                return response.json().get("Balance", 0)
        except Exception as e:
            logger.error(f"(BENTER) Balance check failed: {str(e)}")

        return 0.0


class SMSService:
    """Main SMS Service"""

    def __init__(self, config):
        self.enabled = config.get("enabled", True)
        self.provider_name = config.get("provider", "benter")
        self.providers = {}

        if "benter" in config:
            cfg = config["benter"]
            self.providers["benter"] = BenterSMSProvider(
                api_key=cfg["api_key"],
                client_id=cfg["client_id"],
                sender=cfg["sender"],
                url=cfg["url"],
                balance_url=cfg["balance_url"],
            )

    def send_sms(self, recipient, message):
        """Send SMS"""
        if not self.enabled:
            return {"success": False, "error": "SMS disabled"}

        if self.provider_name not in self.providers:
            return {"success": False, "error": "Provider not found"}

        recipient = self.format_phone(recipient)

        provider = self.providers[self.provider_name]
        return provider.send(recipient, message)

    def send_bulk(self, recipients, message):
        """Send to multiple recipients"""
        results = []
        for recipient in recipients:
            result = self.send_sms(recipient, message)
            result["recipient"] = recipient
            results.append(result)
        return results

    def get_balance(self):
        """Get SMS balance"""
        if self.provider_name not in self.providers:
            return 0.0

        provider = self.providers[self.provider_name]
        if hasattr(provider, "get_balance"):
            return provider.get_balance()
        return 0.0

    def format_phone(self, phone, country_code="255"):
        """Format phone number to international format"""
        phone = str(phone).replace(" ", "").replace("-", "").replace("+", "")

        if phone.startswith("0"):
            phone = country_code + phone[1:]
        elif not phone.startswith(country_code):
            phone = country_code + phone

        return phone


def get_sms_service():
    """Get SMS service instance from Django settings"""
    from django.conf import settings

    config = getattr(settings, "SMS_CONFIG", {})
    return SMSService(config)
