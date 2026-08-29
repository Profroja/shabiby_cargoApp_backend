from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .models import DriverCommissionBand, get_driver_commission


class DriverCommissionTests(TestCase):
    def setUp(self):
        self.band = DriverCommissionBand.objects.create(
            min_distance_km=Decimal("0.00"),
            max_distance_km=Decimal("5.00"),
            commission_percent=Decimal("25.00"),
        )
        DriverCommissionBand.objects.create(
            min_distance_km=Decimal("5.01"),
            max_distance_km=Decimal("10.00"),
            commission_percent=Decimal("30.00"),
        )
        DriverCommissionBand.objects.create(
            min_distance_km=Decimal("10.01"),
            max_distance_km=None,
            commission_percent=Decimal("35.00"),
        )

    def test_below_min_distance_no_band(self):
        DriverCommissionBand.objects.all().delete()
        DriverCommissionBand.objects.create(
            min_distance_km=Decimal("5.00"),
            commission_percent=Decimal("20.00"),
        )
        percent, amount = get_driver_commission(Decimal("2.5"), Decimal("1000"))
        self.assertIsNone(percent)
        self.assertIsNone(amount)

    def test_first_band(self):
        percent, amount = get_driver_commission(Decimal("4.2"), Decimal("2000"))
        self.assertEqual(percent, Decimal("25.00"))
        self.assertEqual(amount, Decimal("500.00"))

    def test_second_band(self):
        percent, amount = get_driver_commission(Decimal("7.0"), Decimal("3000"))
        self.assertEqual(percent, Decimal("30.00"))
        self.assertEqual(amount, Decimal("900.00"))

    def test_open_ended_band(self):
        percent, amount = get_driver_commission(Decimal("55.0"), Decimal("5000"))
        self.assertEqual(percent, Decimal("35.00"))
        self.assertEqual(amount, Decimal("1750.00"))

    def test_inactive_band_ignored(self):
        DriverCommissionBand.objects.filter(id=self.band.id).update(is_active=False)
        percent, amount = get_driver_commission(Decimal("1.0"), Decimal("1000"))
        self.assertIsNone(percent)
        self.assertIsNone(amount)

    def test_missing_fare(self):
        percent, amount = get_driver_commission(Decimal("3.0"), None)
        self.assertIsNone(percent)
        self.assertIsNone(amount)


class DriverCommissionApiTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.User = get_user_model()
        self.admin = self.User.objects.create_user(
            username="admin_com", password="test1234", role="admin"
        )
        self.client = APIClient()
        resp = self.client.post(
            "/api/token/", {"username": "admin_com", "password": "test1234"}
        )
        self.token = resp.json()["access"]

    def test_admin_can_create_and_list_bands(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        resp = self.client.post(
            "/api/commissions/",
            {
                "min_distance_km": "0.00",
                "max_distance_km": "5.00",
                "commission_percent": "25.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        resp = self.client.get("/api/commissions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_non_admin_cannot_create_band(self):
        client = APIClient()
        user = self.User.objects.create_user(
            username="cust_com", password="x", role="customer"
        )
        client.force_authenticate(user=user)
        resp = client.post(
            "/api/commissions/",
            {
                "min_distance_km": "0.00",
                "commission_percent": "25.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_estimate_endpoint(self):
        DriverCommissionBand.objects.create(
            min_distance_km=Decimal("5.01"),
            max_distance_km=Decimal("10.00"),
            commission_percent=Decimal("30.00"),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        resp = self.client.post(
            "/api/commissions/estimate/",
            {"distance_km": 7.0, "fare_amount": 3000},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["commission_percent"], "30.00")
        self.assertEqual(resp.json()["commission_amount"], "900.00")


class CargoTripCommissionSerializerTests(TestCase):
    """Verify the trip serializer surfaces commission fields for the driver app."""

    def _serializer(self):
        from trips.serializers import CargoTripSerializer
        return CargoTripSerializer()

    def test_serializer_exposes_commission_fields(self):
        DriverCommissionBand.objects.create(
            min_distance_km=Decimal("5.01"),
            max_distance_km=Decimal("10.00"),
            commission_percent=Decimal("30.00"),
        )

        trip = type("Trip", (), {})()
        trip.distance_km = Decimal("7.00")
        trip.fare_amount = Decimal("3000.00")

        serializer = self._serializer()
        self.assertEqual(serializer.get_driver_commission_percent(trip), "30.00")
        self.assertEqual(serializer.get_driver_commission_amount(trip), "900.00")

    def test_serializer_returns_none_without_band(self):
        trip = type("Trip", (), {})()
        trip.distance_km = Decimal("7.00")
        trip.fare_amount = Decimal("3000.00")

        serializer = self._serializer()
        self.assertIsNone(serializer.get_driver_commission_percent(trip))
        self.assertIsNone(serializer.get_driver_commission_amount(trip))