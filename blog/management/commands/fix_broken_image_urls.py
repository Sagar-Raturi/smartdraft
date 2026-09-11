import re

from django.core.management.base import BaseCommand

from blog.models import Post

# Before the imagePathAbsolute fix, EasyMDE glued window.location.origin
# onto the front of the already-absolute URL our upload endpoint returned,
# producing content like:
#   ![](https://yoursite.com/https://res.cloudinary.com/cloud/image/upload/uploads/x.png)
# This pulls the real (correct) URL back out from behind the bogus prefix.
BROKEN_IMAGE_URL_RE = re.compile(
    r'!\[([^\]]*)\]\(https?://[^\s)]*?/((?:https?://)[^\s)]+)\)'
)


class Command(BaseCommand):
    help = (
        "Repairs post content saved before the EasyMDE imagePathAbsolute fix, "
        "where uploaded image URLs got a bogus site-origin prefix glued onto "
        "the front of the real (already absolute) image URL. Run without "
        "--apply first to preview what would change."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Save the fix. Without this flag, only reports what would change.',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        fixed_count = 0

        for post in Post.objects.all():
            new_content, n = BROKEN_IMAGE_URL_RE.subn(r'![\1](\2)', post.content)
            if not n:
                continue

            fixed_count += 1
            self.stdout.write(f'Post {post.pk} ("{post.title}"): {n} image URL(s) to fix')
            for match in BROKEN_IMAGE_URL_RE.finditer(post.content):
                self.stdout.write(f'    before: {match.group(0)}')
                self.stdout.write(f'    after:  ![{match.group(1)}]({match.group(2)})')

            if apply_changes:
                post.content = new_content
                post.save(update_fields=['content'])

        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS('No broken image URLs found.'))
        elif apply_changes:
            self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} post(s).'))
        else:
            self.stdout.write(self.style.WARNING(
                f'{fixed_count} post(s) would be fixed. Re-run with --apply to save changes.'
            ))
