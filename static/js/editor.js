/* Markdown editor (EasyMDE) setup for post_form.html.
 *
 * Reads its configuration from data-* attributes on #post-editor-root so
 * this file stays plain, cacheable static JS with no Django template
 * language mixed in.
 */
document.addEventListener('DOMContentLoaded', function () {
    const root = document.getElementById('post-editor-root');
    const textarea = document.getElementById('id_content');
    if (!root || !textarea) {
        return;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const uploadEndpoint = root.dataset.uploadEndpoint;
    const previewEndpoint = root.dataset.previewEndpoint;
    const autosaveId = root.dataset.autosaveId;
    const statusBar = document.getElementById('editor-status-bar');
    const errorBox = document.getElementById('editor-error');

    function debounce(fn, delay) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function showError(message) {
        if (!errorBox) return;
        errorBox.textContent = message;
        errorBox.classList.remove('d-none');
        clearTimeout(showError._t);
        showError._t = setTimeout(() => errorBox.classList.add('d-none'), 6000);
    }

    // Renders preview server-side through the exact same Markdown+sanitizer
    // pipeline as a published post, so the live preview matches reality
    // (EasyMDE's bundled client-side parser doesn't know about our
    // extensions/sanitizer and can render slightly differently).
    let previewRequestId = 0;
    const requestPreview = debounce(function (plainText, preview) {
        const requestId = ++previewRequestId;
        const body = new FormData();
        body.append('text', plainText);

        fetch(previewEndpoint, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: body,
        })
            .then((response) => (response.ok ? response.json() : Promise.reject()))
            .then((data) => {
                if (requestId === previewRequestId) {
                    preview.innerHTML = `<div class="article-content">${data.html}</div>`;
                }
            })
            .catch(() => {
                if (requestId === previewRequestId) {
                    preview.innerHTML = '<p class="text-muted">Preview unavailable.</p>';
                }
            });
    }, 400);

    const easymde = new EasyMDE({
        element: textarea,
        forceSync: true, // guarantees the textarea is updated immediately on submit
        autoDownloadFontAwesome: false,
        uploadImage: true,
        imageUploadEndpoint: uploadEndpoint,
        csrfToken: csrfToken,
        imageCSRFToken: csrfToken,
        // Our upload endpoint already returns a full, ready-to-use URL
        // (an absolute Cloudinary URL in production, a root-relative
        // /media/... path in dev). Without this, EasyMDE prepends
        // window.location.origin to it, producing a broken, doubled-up
        // URL like "https://yoursite.com/https://res.cloudinary.com/..."
        // -- which is why the image failed to render inline.
        imagePathAbsolute: true,
        imageAccept: 'image/png, image/jpeg, image/gif, image/webp',
        imageMaxSize: 5 * 1024 * 1024, // keep in sync with MAX_IMAGE_UPLOAD_SIZE in views.py
        errorCallback: showError,
        toolbar: [
            'bold', 'italic', 'heading', '|',
            'quote', 'unordered-list', 'ordered-list', '|',
            {
                name: 'table',
                action: EasyMDE.drawTable,
                className: 'fa fa-th',
                title: 'Insert Table',
            },
            'horizontal-rule', '|',
            'link', 'upload-image', 'code', '|',
            'preview', 'side-by-side', 'fullscreen', '|',
            'undo', 'redo', '|',
            'guide',
        ],
        previewRender: function (plainText, preview) {
            requestPreview(plainText, preview);
            return preview.innerHTML || 'Loading preview…';
        },
        autosave: {
            enabled: true,
            uniqueId: autosaveId,
            delay: 1000,
        },
        spellChecker: false,
        placeholder: 'Write your content here in Markdown...',
    });

    if (statusBar) {
        const updateStatusBar = function () {
            const text = easymde.value().trim();
            const words = text ? text.split(/\s+/).length : 0;
            const minutes = Math.max(1, Math.round(words / 200));
            statusBar.textContent = `${words} word${words === 1 ? '' : 's'} · ~${minutes} min read`;
        };
        easymde.codemirror.on('change', debounce(updateStatusBar, 200));
        updateStatusBar();
    }
});
