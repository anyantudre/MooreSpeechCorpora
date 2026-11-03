import numpy as np
import soundfile as sf

from fasospeechcorpora import manifest
from fasospeechcorpora.combine import combine
from fasospeechcorpora.config import load_language
from fasospeechcorpora.sources.ipsapps import IpsApps

SR = 16_000


def make_run(root, name, n):
    run = root / name
    (run / "trimmed").mkdir(parents=True)
    rows = []
    for i in range(n):
        sf.write(run / "trimmed" / f"c{i}.wav", np.zeros(SR, dtype=np.float32), SR)
        rows.append({"id": f"c{i}", "audio_filepath": f"trimmed/c{i}.wav", "voice_filepath": f"trimmed/c{i}.wav",
                     "text": "Wẽnnaam yeelame.", "duration": 1.0})
    manifest.write(run / "final.jsonl", rows)
    return run


def test_combine_keeps_ids_unique_and_audio_reachable(tmp_path):
    a, b = make_run(tmp_path, "proverbs", 2), make_run(tmp_path, "tales", 1)
    rows = combine([a, b], tmp_path / "v2")
    assert [r["id"] for r in rows] == ["proverbs_c0", "proverbs_c1", "tales_c0"]
    assert manifest.read(tmp_path / "v2" / "final.jsonl") == rows
    for r in rows:
        assert (tmp_path / "v2" / r["audio_filepath"]).exists() and r["run"] in r["audio_filepath"]


PAGE = """<html><body>
<div class="txs"><span class="bd">1 </span><span class="bd">Ka reng roog la gõeem ye.</span></div>
<audio><source src="https://example.org/{book}.mp3"/></audio>
{next}
</body></html>"""


def test_ipsapps_several_books_prefix_ids(tmp_path, monkeypatch):
    pages = {
        "https://media.ipsapps.org/mos/ora/p1/01-001-001.html": PAGE.format(book="p1", next='<a title="Next Chapter" href="01-001-002.html">n</a>'),
        "https://media.ipsapps.org/mos/ora/p1/01-001-002.html": PAGE.format(book="p1", next=""),
        "https://media.ipsapps.org/mos/ora/p2/01-001-001.html": PAGE.format(book="p2", next=""),
    }

    class Resp:
        def __init__(self, text):
            self.text = text

    src = IpsApps(load_language("mos"), delay=0, start=["https://media.ipsapps.org/mos/ora/p1/01-001-001.html",
                                                         "https://media.ipsapps.org/mos/ora/p2/01-001-001.html"])
    monkeypatch.setattr(src, "get", lambda url: Resp(pages[url]))
    monkeypatch.setattr(src, "download", lambda url, dest: dest)
    records = src.fetch(tmp_path)
    assert [r["id"] for r in records] == ["p1-01-001-001", "p1-01-001-002", "p2-01-001-001"]
    assert records[2]["meta"] == {"chapter": "01-001-001", "book": "p2"}
    assert records[0]["lines"] == ["Ka reng roog la gõeem ye."]
