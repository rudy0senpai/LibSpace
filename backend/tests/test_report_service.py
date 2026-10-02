def test_period_change():
    current, previous = 120, 100
    assert round((current-previous)/previous*100,1) == 20.0

def test_zero_previous_is_null():
    previous=0
    result=None if previous == 0 else 1
    assert result is None
