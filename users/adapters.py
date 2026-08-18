from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_username


class MyAccountAdapter(DefaultAccountAdapter):

    def populate_username(self, request, user):
        email = user_email(user)

        if email:
            base_username = email.split("@")[0]
            username = base_username
            counter = 1

            while user.__class__.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user_username(user, username)

        else:
            super().populate_username(request, user)