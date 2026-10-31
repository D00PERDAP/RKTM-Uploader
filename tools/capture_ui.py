"""Build-only visual QA. Pillow is not imported by the installed application."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from PIL import ImageGrab
import settings
from ui import App

with tempfile.TemporaryDirectory() as temp:
    settings.APP=Path(temp)
    settings.CFG=Path(temp)/'config.json'
    app=App()
    app.geometry('1080x760+0+0')
    output=Path('previews')
    output.mkdir(exist_ok=True)
    # Demonstration rows are local QA fixtures, never uploaded.
    for name in ('raspisan.html', 'm1.html', 'a1.html'):
        path=Path(temp)/name
        path.write_text('<html><body>Preview</body></html>', encoding='utf-8')
        app.entries.append((str(path), name))
    app.refresh()
    for name in ('schedule', 'history', 'settings'):
        app.show_page(name)
        app.update_idletasks()
        app.update()
        app.after(250)
        ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(), app.winfo_rootx()+app.winfo_width(), app.winfo_rooty()+app.winfo_height())).save(output/(name+'.png'))
    app.close()
