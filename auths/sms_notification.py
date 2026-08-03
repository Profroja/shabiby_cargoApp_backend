"""
SMS Notification Module
Handles sending SMS notifications via Benter Group
"""

import logging

from django.utils import timezone

from .sms_service import get_sms_service

logger = logging.getLogger(__name__)


def send_sms_notification(phone_number, message):
    """
    Helper function to send SMS
    """
    try:
        sms = get_sms_service()
        result = sms.send_sms(phone_number, message)

        logger.info(
            f"SMS to {phone_number} | provider={sms.provider_name} "
            f"| success={result.get('success', False)} "
            f"| response={result.get('response', result.get('error', {}))}"
        )

        if result.get("success"):
            return True
        else:
            logger.error(f"SMS failed to {phone_number}: {result.get('error')}")
            return False

    except Exception as e:
        logger.error(f"SMS exception for {phone_number}: {str(e)}")
        return False
