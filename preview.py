"""Preview the existing Jekyll build: python3 preview.py (no Docker required)."""
import io
import re
from html import escape
import markdown
import yaml
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BUILD = Path(__file__).resolve().parent / "_site"
ROOT = BUILD.parent


def render_home(html):
    """Refresh the simple Markdown homepage inside the compiled theme shell."""
    source = (ROOT / "_pages/about.md").read_text(encoding="utf-8")
    content = markdown.markdown(source.split('---', 2)[2], extensions=['toc'])
    html = re.sub(r'(<section class="page__content"[^>]*>).*?(</section>)',
                  lambda m: m[1] + content + m[2], html, count=1, flags=re.S)
    config = yaml.safe_load((ROOT / '_config.yml').read_text())
    scholar = escape(config['author']['googlescholar'], quote=True)
    # Replace existing Scholar link, or add it to a build made before configuration.
    html = re.sub(r'<li>\s*<a[^>]*href="https://scholar.google.com/[^\"]*".*?</li>', '', html, flags=re.S)
    html = re.sub(r'(<ul class="author__urls[^\"]*">)',
                  lambda m: m[1] + '<li><a href="' + scholar + '"><i class="ai ai-google-scholar" aria-hidden="true"></i> Google Scholar</a></li>', html, count=1)
    navigation = yaml.safe_load((ROOT / '_data/navigation.yml').read_text())['main']
    links = '<li class="masthead__menu-item masthead__menu-item--lg"><a href="/">Liangtao Dai</a></li>'
    links += ''.join('<li class="masthead__menu-item"><a href="' + escape(item['url'], quote=True) + '">' + escape(item['title']) + '</a></li>' for item in navigation)
    html = re.sub(r'(<ul class="visible-links">).*?(</ul>)', lambda m: m[1] + links + m[2], html, count=1, flags=re.S)
    return html


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BUILD), **kwargs)

    def send_head(self):
        # Keep this preview confined to the generated site, including symlinks.
        path = Path(self.translate_path(self.path)).resolve()
        if not path.is_relative_to(BUILD.resolve()):
            self.send_error(403)
            return None
        if path.is_dir():
            path = path / "index.html"
        if path.is_file() and path.suffix == ".html":
            html = path.read_text(encoding="utf-8")
            if path == BUILD / 'index.html':
                html = render_home(html)
            # Old builds used the Jekyll bind address as their public origin.
            html = re.sub(r'https?://(?:0\.0\.0\.0|localhost|127\.0\.0\.1):4000', '', html)
            # Use the actual compiled Academic Pages theme, without overrides.
            html = re.sub(r'<link\b[^>]*href="[^"]*/assets/css/fallback\.css"[^>]*>', '', html)
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return io.BytesIO(data)
        return super().send_head()


if __name__ == "__main__":
    if not (BUILD / "index.html").exists():
        raise SystemExit("No generated site found in _site. Run a Jekyll build first.")
    server = ThreadingHTTPServer(("127.0.0.1", 8000), PreviewHandler)
    print("Preview: http://localhost:8000", flush=True)
    print("Homepage content refreshes from _pages/about.md on reload. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
