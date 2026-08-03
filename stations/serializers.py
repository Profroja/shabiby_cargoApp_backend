from rest_framework import serializers

from .models import CargoStation


class CargoStationSerializer(serializers.ModelSerializer):
    center_name = serializers.CharField(source="name", required=False)
    location = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CargoStation
        fields = (
            "id",
            "center_name",
            "location",
            "branch_code",
            "region",
            "city",
            "address",
            "latitude",
            "longitude",
            "zone",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def create(self, validated_data):
        location = validated_data.pop("location", None)
        if location and "region" not in validated_data:
            parts = [p.strip() for p in location.split(",")]
            if parts:
                validated_data.setdefault("region", parts[0])
            if len(parts) > 1:
                validated_data.setdefault("city", parts[1])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        location = validated_data.pop("location", None)
        if location:
            parts = [p.strip() for p in location.split(",")]
            if parts:
                instance.region = parts[0]
            if len(parts) > 1:
                instance.city = parts[1]
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        parts = [p for p in [instance.region, instance.city] if p]
        ret["location"] = ", ".join(parts)
        return ret
