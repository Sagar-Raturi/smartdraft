from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Post
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

import uuid
from PIL import Image, UnidentifiedImageError
from django.core.files.storage import default_storage
from django.http import JsonResponse

from .markdown_utils import render_markdown_safe

# Server-side guardrails for the Markdown editor's image upload. The client
# already restricts the file picker to these types, but that's only a UX
# hint -- an attacker can send any bytes with any Content-Type header, so
# everything here is re-checked against the actual file.
ALLOWED_IMAGE_TYPES = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp',
}
MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

# # def home(request): 
# # 	context = {'posts': Post.objects.all()}
# # 	return render(request, 'blog/home.html', context)

# 	def form_valid(self, form):
# 		form.instance.autuor = self.request.user
# 		return super().form_valid(form)

def about(request):
	return HttpResponse('This is about page')


class PostListView(ListView):
	model = Post
	template_name = 'blog/home.html'
	context_object_name = 'posts'
	ordering = ['-date_posted']
	paginate_by = 5

class UserPostListView(ListView):
	model = Post 
	template_name = 'blog/user_posts.html'
	context_object_name = 'posts'
	paginate_by = 5

	def get_queryset(self):
		user = get_object_or_404(User, username=self.kwargs.get('username'))
		return Post.objects.filter(author=user).order_by('-date_posted')

class PostDetailView(DetailView):
	model = Post

class PostCreateView(LoginRequiredMixin, CreateView):
	model = Post
	fields = ['title', 'content']

	def form_valid(self, form):
		form.instance.author = self.request.user 
		return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
	model = Post 
	fields = ['title', 'content']

	def form_valid(self, form):
		form.instance.author = self.request.user 
		return super().form_valid(form)

	def test_func(self):
		post = self.get_object()
		if self.request.user == post.author:
			return True 
		return False

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
	model = Post 
	success_url = '/'

	def test_func(self):
		post = self.get_object()
		if self.request.user == post.author:
			return True
		return False 

@login_required
def upvote_post(request, slug):
	post = get_object_or_404(Post, slug=slug)

	if post.upvotes.filter(id=request.user.id).exists():
		post.upvotes.remove(request.user)
	else:
		post.upvotes.add(request.user)

	return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
@require_POST
def upload_image(request):
    # EasyMDE sends the uploaded file in request.FILES['image']
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({'error': 'No image provided.'}, status=400)

    if image.size > MAX_IMAGE_UPLOAD_SIZE:
        return JsonResponse({'error': 'Image is too large (max 5MB).'}, status=400)

    extension = ALLOWED_IMAGE_TYPES.get(image.content_type)
    if not extension:
        return JsonResponse({'error': 'Unsupported image type.'}, status=400)

    # Confirm the bytes are actually a valid image of the claimed type
    # (a browser-set Content-Type header can't be trusted on its own).
    try:
        with Image.open(image) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        return JsonResponse({'error': 'File is not a valid image.'}, status=400)
    finally:
        image.seek(0)

    # Random filename: never trust the client-supplied name (path traversal,
    # collisions, unicode/control characters).
    filename = f"uploads/{uuid.uuid4().hex}.{extension}"

    # default_storage resolves to whatever STORAGES["default"] is configured
    # to (Cloudinary in production, local disk in dev) -- unlike a
    # hardcoded FileSystemStorage, this actually persists in production.
    saved_name = default_storage.save(filename, image)
    uploaded_file_url = default_storage.url(saved_name)

    # EasyMDE requires this exact JSON response
    return JsonResponse({
        "data": {
            "filePath": uploaded_file_url
        }
    })


@login_required
@require_POST
def render_preview(request):
    """Render Markdown source exactly the way a published post would.

    Used by the editor's live preview so what the author sees while
    writing matches the real post (same extensions, same sanitizer),
    instead of EasyMDE's bundled client-side Markdown parser.
    """
    text = request.POST.get('text', '')
    return JsonResponse({'html': render_markdown_safe(text)})




