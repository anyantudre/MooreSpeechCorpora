import numpy as np

from fasospeechcorpora.transcribe import ASR, cer, score_text


def fake_asr(batch_size=8, max_batch_seconds=60.0):
    asr = ASR.__new__(ASR)
    asr.batch_size, asr.max_batch_seconds = batch_size, max_batch_seconds
    asr.calls = []

    def pipe(inputs, batch_size):
        asr.calls.append(len(inputs))
        return [{"text": f" {len(x['raw'])} "} for x in inputs]

    asr.pipe = pipe
    return asr


def test_batches_cap_clips_and_padded_seconds():
    asr = fake_asr(batch_size=3, max_batch_seconds=10)
    # lengths in seconds at sr=1: three short clips, two 4 s clips, one 30 s clip alone
    assert asr.batches([1, 4, 2, 30, 1, 4], 1) == [[0, 4, 2], [1, 5], [3]]


def test_asr_keeps_input_order():
    asr = fake_asr(batch_size=2)
    clips = [np.zeros(n, dtype=np.float32) for n in (5, 1, 4, 2, 3)]
    assert asr(clips) == ["5", "1", "4", "2", "3"]
    assert asr.calls == [2, 2, 1]


def test_cer_ignores_case_and_punctuation():
    assert cer("Wẽnnaam yeelame.", "wẽnnaam yeelame") == 0.0


def test_score_text_splits_apostrophes_and_hyphens_and_keeps_marks():
    assert score_text("T’a yõk-a <MUSIC> «Ad paoor»!") == "t a yõk a ad paoor"
    assert score_text("ɛ̃ ka") == "ɛ̃ ka"           # a tilde with no precomposed form stays
    assert cer("Pʋg rʋmd ka mi t'a sɩd", "pʋg rʋmd ka mi t a sɩd") == 0.0
