from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

class Post(models.Model):
	title = models.CharField(max_length=100)
	content = models.TextField()
	date_posted = models.DateTimeField(default=timezone.now)
	author = models.ForeignKey(User, on_delete=models.CASCADE)
	slug = models.SlugField(max_length=250, unique=True)
	upvotes = models.ManyToManyField(User, related_name='upvoted_posts', blank=True)

	def total_upvotes(self):
		return self.upvotes.count()

	def save(self, *args, **kwargs):
		if not self.slug:
			base_slug = slugify(self.title).replace(' ', '_')
			slug = base_slug
			counter = 1

			while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
				slug = f"{base_slug}_{counter}"
				counter += 1

			self.slug = slug 
		super().save(*args, **kwargs)

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('post-detail', kwargs={'slug': self.slug})
