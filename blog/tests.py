import io
import shutil
import tempfile

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.storage import Storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .management.commands.fix_broken_image_urls import BROKEN_IMAGE_URL_RE
from .markdown_utils import render_markdown_safe
from .templatetags.blog_tags import markdown_excerpt
from .models import Post

TEST_MEDIA_ROOT = tempfile.mkdtemp()

# Route uploads to local disk for these tests instead of the real
# Cloudinary account configured in settings.
LOCAL_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


def make_png_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


class FakeAbsoluteURLStorage(Storage):
    """Stands in for MediaCloudinaryStorage in tests: stores bytes in memory
    but, like Cloudinary, .url() returns a fully-qualified absolute URL
    rather than a site-relative path. Lets us prove the upload -> Markdown
    -> render pipeline behaves correctly against that shape of URL without
    making a real network call to Cloudinary.
    """

    _files = {}

    def _save(self, name, content):
        self._files[name] = content.read()
        return name

    def exists(self, name):
        return name in self._files

    def url(self, name):
        return f'https://fake-cdn.example.com/{name}'

    def size(self, name):
        return len(self._files.get(name, b''))

    def get_available_name(self, name, max_length=None):
        return name


ABSOLUTE_URL_STORAGES = {
    'default': {'BACKEND': 'blog.tests.FakeAbsoluteURLStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


class MarkdownRenderingTests(TestCase):
    def test_script_tags_are_stripped(self):
        html = render_markdown_safe('Hello <script>alert(1)</script> world')
        self.assertNotIn('<script', html)

    def test_basic_formatting_survives(self):
        html = render_markdown_safe('# Title\n\n**bold** and *italic*')
        self.assertIn('<h1', html)
        self.assertIn('<strong>bold</strong>', html)

    def test_image_tags_survive(self):
        html = render_markdown_safe('![alt text](https://example.com/a.png)')
        self.assertIn('<img', html)
        self.assertIn('src="https://example.com/a.png"', html)

    def test_javascript_protocol_is_stripped(self):
        html = render_markdown_safe('[click me](javascript:alert(1))')
        self.assertNotIn('javascript:', html)

    def test_empty_input(self):
        self.assertEqual(render_markdown_safe(''), '')
        self.assertEqual(render_markdown_safe(None), '')


class MarkdownExcerptTests(TestCase):
    def test_short_text_is_unchanged(self):
        self.assertEqual(markdown_excerpt('Hello world', 10), 'Hello world')

    def test_long_text_is_truncated_with_ellipsis(self):
        text = ' '.join(f'word{i}' for i in range(50))
        excerpt = markdown_excerpt(text, 5)
        self.assertTrue(excerpt.endswith('…'))
        self.assertEqual(len(excerpt.rstrip('…').split()), 5)

    def test_markdown_syntax_does_not_leak_into_excerpt(self):
        excerpt = markdown_excerpt('**bold** and `code`', 10)
        self.assertNotIn('*', excerpt)
        self.assertNotIn('`', excerpt)


@override_settings(STORAGES=LOCAL_STORAGES, MEDIA_ROOT=TEST_MEDIA_ROOT)
class UploadImageViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author', password='pw12345')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client.login(username='author', password='pw12345')
        self.url = reverse('upload-image')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url, {'image': SimpleUploadedFile(
            'a.png', make_png_bytes(), content_type='image/png')})
        self.assertNotEqual(response.status_code, 200)

    def test_rejects_missing_file(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)

    def test_rejects_disallowed_content_type(self):
        upload = SimpleUploadedFile('a.txt', b'not an image', content_type='text/plain')
        response = self.client.post(self.url, {'image': upload})
        self.assertEqual(response.status_code, 400)

    def test_rejects_oversized_file(self):
        from . import views as blog_views
        oversized = SimpleUploadedFile(
            'a.png', b'\x00' * (blog_views.MAX_IMAGE_UPLOAD_SIZE + 1), content_type='image/png')
        response = self.client.post(self.url, {'image': oversized})
        self.assertEqual(response.status_code, 400)

    def test_rejects_bytes_that_are_not_really_an_image(self):
        # Correct content-type header, but the payload isn't valid PNG data --
        # e.g. a renamed script. Pillow's verify() must catch this.
        fake = SimpleUploadedFile('a.png', b'this is not png data', content_type='image/png')
        response = self.client.post(self.url, {'image': fake})
        self.assertEqual(response.status_code, 400)

    def test_accepts_valid_png(self):
        upload = SimpleUploadedFile('a.png', make_png_bytes(), content_type='image/png')
        response = self.client.post(self.url, {'image': upload})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('filePath', data['data'])

    def test_uploaded_filename_is_not_client_controlled(self):
        upload = SimpleUploadedFile('../../evil.png', make_png_bytes(), content_type='image/png')
        response = self.client.post(self.url, {'image': upload})
        self.assertEqual(response.status_code, 200)
        file_path = response.json()['data']['filePath']
        self.assertNotIn('evil', file_path)
        self.assertNotIn('..', file_path)


class RenderPreviewViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author2', password='pw12345')

    def setUp(self):
        self.client.login(username='author2', password='pw12345')
        self.url = reverse('render-preview')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url, {'text': '# Hi'})
        self.assertNotEqual(response.status_code, 200)

    def test_renders_and_sanitizes(self):
        response = self.client.post(self.url, {'text': '# Hi <script>alert(1)</script>'})
        self.assertEqual(response.status_code, 200)
        html = response.json()['html']
        self.assertIn('<h1', html)
        self.assertNotIn('<script', html)


@override_settings(STORAGES=ABSOLUTE_URL_STORAGES)
class ImageUploadEndToEndTests(TestCase):
    """Proves the full pipeline against an absolute-URL storage backend --
    the exact shape Cloudinary uses in production -- without hitting the
    real Cloudinary API.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author3', password='pw12345')

    def setUp(self):
        FakeAbsoluteURLStorage._files.clear()
        self.client.login(username='author3', password='pw12345')

    def test_uploaded_image_renders_inline_in_the_published_post(self):
        upload = SimpleUploadedFile('photo.png', make_png_bytes(), content_type='image/png')
        response = self.client.post(reverse('upload-image'), {'image': upload})
        self.assertEqual(response.status_code, 200)

        file_path = response.json()['data']['filePath']
        self.assertTrue(file_path.startswith('https://fake-cdn.example.com/'))

        # This is exactly what EasyMDE inserts into the textarea with
        # imagePathAbsolute: true -- filePath used as-is, no origin prefix.
        markdown_source = f'![]({file_path})'

        post = Post.objects.create(title='Test post', content=markdown_source, author=self.user)
        html = render_markdown_safe(post.content)

        self.assertIn(f'<img alt="" src="{file_path}">', html)

    def test_without_imagepathabsolute_the_url_would_have_been_broken(self):
        # Documents the bug we fixed: this is what the OLD editor.js config
        # (imagePathAbsolute defaulting to false) would have produced --
        # confirms the repair regex in fix_broken_image_urls recognizes it.
        upload = SimpleUploadedFile('photo.png', make_png_bytes(), content_type='image/png')
        response = self.client.post(reverse('upload-image'), {'image': upload})
        file_path = response.json()['data']['filePath']

        broken_markdown = f'![](https://yoursite.com/{file_path})'
        self.assertRegex(broken_markdown, BROKEN_IMAGE_URL_RE)

        fixed_markdown = BROKEN_IMAGE_URL_RE.sub(r'![\1](\2)', broken_markdown)
        self.assertEqual(fixed_markdown, f'![]({file_path})')
