from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

class Command(BaseCommand):
    help = 'Crea un superusuario por defecto si no existe.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = settings.SUPERUSER_USERNAME
        email = settings.SUPERUSER_EMAIL
        password = settings.SUPERUSER_PASSWORD

        if not all([username, email, password]):
            self.stdout.write(self.style.WARNING('Faltan variables de entorno para crear el superusuario. Saltando.'))
            return

        if not User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f"Creando superusuario por defecto: {username}"))
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS("✅ Superusuario creado exitosamente."))
        else:
            self.stdout.write(self.style.WARNING(f"El superusuario '{username}' ya existe. No se realizaron acciones."))