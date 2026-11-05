import sys
sys.path.insert(0, "worker")
from clean import clean, classify  # noqa: E402


def rec(i, text, raw):
    return {"id": i, "text": text, "teacher_raw": raw}


GOOD = '{"intent": "weather_query", "date": null, "time": null, "place": "london"}'


def test_classify_reasons():
    t = "what is the weather in london"
    assert classify(rec("1", t, GOOD)) is None
    assert classify(rec("1", t, "nope")) == "a"
    assert classify(rec("1", t, '{"intent": "weather_query"}')) == "b"
    assert classify(rec("1", t, GOOD.replace("weather_query", "play_music"))) == "c"
    assert classify(rec("1", t, GOOD.replace("london", "paris"))) == "d"


def test_counts_balance_and_dedupe():
    t = "what is the weather in london"
    records = [rec("C2", t, GOOD), rec("C1", t, GOOD), rec("C3", t, "bad"), rec("C4", "x", GOOD)]
    out, c = clean(records)
    assert [r["id"] for r in out] == ["C1"]  # smallest id kept
    assert c["duplicates"] == 1 and c["a"] == 1 and c["d"] == 1
    assert c["input"] == c["a"] + c["b"] + c["c"] + c["d"] + c["duplicates"] + c["kept"]
