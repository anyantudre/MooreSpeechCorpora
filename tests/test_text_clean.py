from fasospeechcorpora.text import clean_text


def test_leading_number_and_space_before_punctuation():
    assert clean_text("1 A Yamne kibare .") == "A Yamne kibare."
    assert clean_text("7 Põor naaf zomdame t'a ket n gãe tẽnga.") == "Põor naaf zomdame t'a ket n gãe tẽnga."


def test_apostrophes_and_dialogue_dash():
    assert clean_text("t’a kẽem-dãmbã tõdge.") == "t'a kẽem-dãmbã tõdge."
    assert clean_text("La bãmb me sok-a lame:- Fo sẽn gomd") == "La bãmb me sok-a lame: Fo sẽn gomd"


def test_doubled_sentence_keeps_one_copy():
    assert clean_text("Bõnpoak yãnd yaa yẽ bg yãnde. Bõnpoak yãnd yaa yẽbg yãnde.") == "Bõnpoak yãnd yaa yẽbg yãnde."
    assert clean_text("Ka reng roog la gõeem ye.") == "Ka reng roog la gõeem ye."


def test_words_are_not_changed():
    text = "Kom-pugli a tãab n wa n tũ taab n kẽng raad wɩɩsgo, «Bɩ d kẽnge!»"
    assert clean_text(text) == text
