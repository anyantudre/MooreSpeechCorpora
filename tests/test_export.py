from fasospeechcorpora.export import make_pairs


def clip(i, page, lang, text, start, end):
    return {"id": f"{page}_{i:04d}", "audio_filepath": f"clips/{page}/{page}_{i:04d}.wav", "text": text,
            "language": lang, "source_id": page, "start": start, "end": end, "duration": end - start}


def test_proverb_read_twice_gives_two_pairs_sharing_the_french():
    rows = [clip(0, "p1", "mos", "Ka reng roog la gõeem ye.", 0.0, 2.7),
            clip(1, "p1", "fra", "Se coucher avant les autres ne fait pas dormir avant eux.", 3.0, 8.4),
            clip(2, "p1", "mos", "Ka reng roog la gõeem ye.", 8.6, 11.5)]
    pairs = make_pairs(rows, "mos", "fra", ("moore", "french"))
    assert [p["moore_audio"] for p in pairs] == ["clips/p1/p1_0000.wav", "clips/p1/p1_0002.wav"]
    assert {p["french_audio"] for p in pairs} == {"clips/p1/p1_0001.wav"}
    assert pairs[0]["chapter"] == "p1"
    assert list(pairs[0]) == ["id", "moore_audio", "moore_text", "french_text", "french_audio",
                              "duration_moore", "duration_french", "chapter"]


def test_each_proverb_pairs_with_its_own_translation():
    rows = [clip(0, "p", "mos", "A.", 0, 2), clip(1, "p", "fra", "a.", 2, 4),
            clip(2, "p", "mos", "B.", 4, 6), clip(3, "p", "fra", "b.", 6, 8)]
    pairs = make_pairs(rows, "mos", "fra")
    assert [(p["mos_text"], p["fra_text"]) for p in pairs] == [("A.", "a."), ("B.", "b.")]


def test_no_pair_across_another_proverb():
    rows = [clip(0, "p", "mos", "A.", 0, 2), clip(2, "p", "mos", "B.", 4, 6), clip(3, "p", "fra", "b.", 6, 8)]
    assert [p["mos_text"] for p in make_pairs(rows, "mos", "fra")] == ["B."]
