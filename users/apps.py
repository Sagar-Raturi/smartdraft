from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_fields = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        import users.signals
