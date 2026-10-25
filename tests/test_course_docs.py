"""Exercise document navigation and its filesystem boundary without live services."""
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('course_docs_studio', ROOT / 'system/services/studio/studio.py')
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


@pytest.fixture
def docs(tmp_path, monkeypatch):
    root = tmp_path / 'course'
    root.mkdir()
    (root / 'diagrams').mkdir()
    (root / 'guide.md').write_text('# Course\n\n## Start and stop\n\n![Map](diagrams/map.svg)\n\n<script>alert(1)</script>\n\n## Start and stop\n')
    (root / 'diagrams/map.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (root / 'outside.svg').write_text('<svg/>')
    (root / 'secret.txt').write_text('not a document')
    (tmp_path / 'outside.md').write_text('outside the course')
    (root / 'escape.md').symlink_to(tmp_path / 'outside.md')
    monkeypatch.setenv('COURSE_DOCS_DIR', str(root))
    # No lifespan context: these checks must not subscribe to registry/planner.
    client = TestClient(studio.app)
    yield client
    client.close()


def test_document_images_anchors_and_html_escaping(docs):
    result = docs.get('/course/guide.md')
    assert result.status_code == 200
    assert 'src="diagrams/map.svg"' in result.text
    assert 'id="start-and-stop"' in result.text
    assert 'id="start-and-stop-1"' in result.text
    assert '<script>' not in result.text
    assert '&lt;script&gt;' in result.text
    assert '/course/sessions/session-03-eve/ADOPTION.md' in result.text


def test_diagram_has_image_type_and_restricted_direct_view(docs):
    result = docs.get('/course/diagrams/map.svg')
    assert result.status_code == 200
    assert result.headers['content-type'] == 'image/svg+xml'
    assert result.headers['x-content-type-options'] == 'nosniff'
    assert 'sandbox' in result.headers['content-security-policy']


@pytest.mark.parametrize('path', [
    'outside.svg', 'secret.txt', 'missing.md', 'escape.md',
    '%2e%2e%2foutside.md', 'diagrams/%2e%2e%2foutside.svg',
])
def test_document_route_does_not_expand_repo_access(docs, path):
    assert docs.get('/course/' + path).status_code == 404


def test_real_course_guides_and_all_diagrams(monkeypatch):
    monkeypatch.setenv('COURSE_DOCS_DIR', str(ROOT / 'course'))
    client = TestClient(studio.app)
    for path in ['COURSE.md', 'INSTRUCTOR.md', 'VALIDATION.md', 'pre-work/SETUP.md',
                 'ARCHITECTURE.md', 'sessions/session-03-eve/ADOPTION.md',
                 'sessions/session-03-eve/DIRECTORY.md']:
        assert client.get('/course/' + path).status_code == 200
    for path in (ROOT / 'course/sessions').glob('session-*/WALKTHROUGH.md'):
        assert client.get('/course/' + path.relative_to(ROOT / 'course').as_posix()).status_code == 200
    for path in (ROOT / 'course/diagrams').glob('*.svg'):
        assert client.get('/course/diagrams/' + path.name).status_code == 200
    client.close()


@pytest.mark.parametrize('old,new', [
    ('REVISED-COURSE.md', 'COURSE.md'),
    ('REVISED-INSTRUCTOR.md', 'INSTRUCTOR.md'),
    ('REVISED-VALIDATION.md', 'VALIDATION.md'),
    ('pre-work/00-setup-and-api-access.md', 'pre-work/SETUP.md'),
    ('pre-work/01-revised-model-access.md', 'pre-work/SETUP.md'),
])
def test_old_bookmarks_redirect_to_the_single_current_document(monkeypatch, old, new):
    monkeypatch.setenv('COURSE_DOCS_DIR', str(ROOT / 'course'))
    client = TestClient(studio.app, follow_redirects=False)
    result = client.get('/course/' + old)
    assert result.status_code == 308
    assert result.headers['location'] == '/course/' + new
    client.close()


def test_repository_source_links_work_without_exposing_more_local_files(monkeypatch):
    monkeypatch.setenv('COURSE_DOCS_DIR', str(ROOT / 'course'))
    client = TestClient(studio.app)
    page = client.get('/course/sessions/session-03-eve/WALKTHROUGH.md')
    assert 'https://github.com/AgentOrientedArchitecture/aoa-course/blob/main/course/sessions/session-01-cv-fit/cv-examples/jordan-okafor.txt' in page.text
    assert 'href="../../pre-work/SETUP.md"' in page.text
    overview = client.get('/course/ARCHITECTURE.md')
    assert 'https://github.com/AgentOrientedArchitecture/aoa-course/blob/main/system/services/planner/planner.py' in overview.text
    assert 'src="diagrams/components.svg"' in overview.text
    assert client.get('/course/../system/services/planner/planner.py').status_code == 404
    folder = client.get('/course/sessions/', follow_redirects=False)
    assert folder.status_code == 308
    assert folder.headers['location'] == '/course/sessions/README.md'
    client.close()
