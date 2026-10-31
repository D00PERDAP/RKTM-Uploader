from pathlib import Path


def test_inno_unicode_source_and_brand_assets():
    root=Path(__file__).resolve().parents[1]
    data=(root/'installer.iss').read_bytes()
    assert data.startswith(b'\xef\xbb\xbf'), 'Inno 6.2 requires UTF-8 BOM for Cyrillic source'
    text=data.decode('utf-8-sig')
    assert 'AppName=РКТМ — Расписание' in text
    assert 'WelcomeLabel1=Установка РКТМ — Расписание' in text
    for name in ('setup-welcome.bmp', 'setup-logo.bmp'):
        assert (root/'assets'/name).read_bytes().startswith(b'BM')
