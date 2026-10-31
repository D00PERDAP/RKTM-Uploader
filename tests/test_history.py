import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import history
import settings


def test_history_counts_only_and_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'APP', tmp_path)
    history.record(3, 2)
    history.record(8, 8)
    rows=history.recent()
    assert [r[1:] for r in rows]==[(8, 8), (3, 2)]
    assert len(history.recent(1))==1
    with history.connect() as db:
        names=[r[1] for r in db.execute('PRAGMA table_info(publications)')]
    assert names==['id', 'date', 'total', 'succeeded']
