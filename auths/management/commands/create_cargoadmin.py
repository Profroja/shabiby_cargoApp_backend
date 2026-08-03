from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the cargoadmin API user"

    def handle(self, *args, **options):
        User = get_user_model()
        username = "cargoadmin"
        password = "cargoadmin12345"

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"User '{username}' already exists.")
            )
            return

        User.objects.create_user(
            username=username,
            password=password,
            first_name="Cargo",
            last_name="Admin",
            phone_number="0000000000",
            role="admin",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"User '{username}' created successfully."
            )
        )
