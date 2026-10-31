import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
pytestmark=pytest.mark.skipif(sys.platform!='win32', reason='Real Windows Tk widgets required')


@pytest.fixture
def app(tmp_path, monkeypatch):
    import settings
    from ui import App
    monkeypatch.setattr(settings, 'APP', tmp_path)
    monkeypatch.setattr(settings, 'CFG', tmp_path/'config.json')
    a=App()
    a.update()
    yield a
    a.close()


def test_same_window_tabs_and_selection(app, tmp_path):
    for name in ('schedule', 'history', 'settings'):
        app.show_page(name)
        app.update()
        assert app.pages[name].winfo_ismapped()
        assert len([p for p in app.pages.values() if p.winfo_ismapped()])==1
    app.show_page('schedule')
    p=tmp_path/'one.html'
    p.write_text('<html>1</html>')
    app.append([(str(p), p.name)])
    assert len(app.items.get_children())==1
    app.items.selection_set('0')
    app.remove_selected()
    assert not app.entries
    assert not app.items.get_children()


def test_review_and_busy_guards(app, tmp_path):
    from core import UploadError
    p=tmp_path/'one.html'
    p.write_text('<html>1</html>')
    app.append([(str(p), p.name)])
    app.cfg={'host':'example.org', 'user':'rktm', 'port':'22', 'password':'test', 'hostkey':'ssh-ed25519 256 SHA256:'+'A'*43, 'folder':'/HTML'}
    app.review()
    assert app.stage_num==2
    assert 'disabled' in app.import_buttons[0].state()
    app.busy=True
    app.show_page('history')
    app.show_stage(1)
    assert app.current_page=='schedule'
    assert app.stage_num==2
    app.busy=False
    app.show_stage(1)
    with pytest.raises(UploadError):app.append([(str(p), p.name)])
    assert len(app.entries)==1
    p.unlink()
    with pytest.raises(UploadError):app.validate_entries()


def test_dpapi_roundtrip_on_current_architecture(tmp_path, monkeypatch):
    import settings
    monkeypatch.setattr(settings, 'APP', tmp_path)
    monkeypatch.setattr(settings, 'CFG', tmp_path/'config.json')
    c={'host':'example.org', 'user':'rktm', 'port':'22', 'password':'Тестовый пароль', 'hostkey':'test', 'folder':'/HTML'}
    settings.save(c)
    assert settings.load()==c
    assert c['password'] not in settings.CFG.read_text(encoding='utf-8')


def test_publish_action_visible_on_small_display(app):
    app.geometry('960x640')
    app.update()
    b=app.send_button
    assert b.winfo_ismapped()
    assert b.winfo_rooty()+b.winfo_height() < app.winfo_rooty()+app.winfo_height()-25
    assert app.items.winfo_height()>=30
