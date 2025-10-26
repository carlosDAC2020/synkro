from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    # --- INICIO DE LA MODIFICACIÓN ---
    def ready(self):
        """
        Este método se ejecuta cuando la aplicación está lista.
        Es el lugar ideal para tareas de inicialización.
        """
        # Importamos aquí para evitar errores de importación circular o de apps no cargadas
        from django.conf import settings
        from django.contrib.auth import get_user_model

        # Obtenemos el modelo de Usuario que estés usando
        User = get_user_model()

        # Verificamos si las variables de entorno están definidas
        username = settings.SUPERUSER_USERNAME
        email = settings.SUPERUSER_EMAIL
        password = settings.SUPERUSER_PASSWORD

        if not all([username, email, password]):
            # Si falta alguna variable, simplemente no hacemos nada y podríamos advertirlo
            print("ADVERTENCIA: Faltan variables de entorno para crear el superusuario.")
            return

        # LA LÓGICA CLAVE: Solo crear el usuario si NO existe
        if not User.objects.filter(username=username).exists():
            print(f"Creando superusuario por defecto: {username}...")
            
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            print("✅ Superusuario creado exitosamente.")
        else:
            print(f"El superusuario '{username}' ya existe. No se realizaron acciones.")
    # --- FIN DE LA MODIFICACIÓN ---