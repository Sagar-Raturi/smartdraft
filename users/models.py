from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django_resized import ResizedImageField

class Profile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	image = ResizedImageField(size=[600,600], quality=85, default='default.jpg', upload_to="profile_pics")

	def __str__(self):
		return f'{self.user.username} Profile'
	
