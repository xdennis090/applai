import sys
import secrets
import getpass

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError, ProgrammingError


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        post_migrate.connect(self.create_default_admin, sender=self)

    def create_default_admin(self, **kwargs):
        # Prompt to create a superuser in development so new clones have admin access.
        if not settings.DEBUG:
            return
        try:
            User = get_user_model()
            if User.objects.filter(is_superuser=True).exists():
                return

            default_username = settings.DEFAULT_ADMIN_USERNAME
            default_email = settings.DEFAULT_ADMIN_EMAIL
            default_password = settings.DEFAULT_ADMIN_PASSWORD

            if not sys.stdin.isatty():
                print(
                    "[accounts] Kein Superuser gefunden. "
                    "Bitte interaktiv `createsuperuser` ausführen oder DEFAULT_ADMIN_* Umgebungsvariablen setzen."
                )
                return

            print("\n[accounts] Kein Admin-User gefunden. Jetzt anlegen:")
            confirm = input("Admin jetzt erstellen? [Y/n]: ").strip().lower()
            if confirm not in ("", "y", "yes", "j", "ja"):
                print("[accounts] Übersprungen. Später mit `python manage.py createsuperuser` anlegen.")
                return

            username = input(f"Admin-Username [{default_username}]: ").strip() or default_username
            email = input(f"Admin-E-Mail [{default_email}]: ").strip() or default_email
            password = getpass.getpass("Admin-Passwort (leer = zufällig generiert): ").strip()
            if not password:
                password = default_password or secrets.token_urlsafe(12)
                print(f"[accounts] Passwort generiert: {password}")

            User.objects.create_superuser(username=username, email=email, password=password)
            print(f"[accounts] Admin erstellt: {username}")
        except (OperationalError, ProgrammingError):
            # Database not ready (migrations pending); skip silently.
            return
