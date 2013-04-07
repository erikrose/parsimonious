from example_json import json


def test_numbers():
    assert json.loads('5') == 5
    assert json.loads('55') == 55
    assert json.loads('-5') == -5
    assert json.loads('5.5') == 5.5
    assert json.loads('5e-2') == 5e-2
    assert json.loads('5.3e-2') == 5.3e-2


def test_strings():
    assert json.loads('""') == ''
    assert json.loads('"hai"') == 'hai'


def test_true_false_null():
    assert json.loads('true') == True
    assert json.loads('false') == False
    assert json.loads('null') == None


def test_arrays():
    assert json.loads('[]') == []
    assert json.loads('[1]') == [1]
    assert json.loads('["a",1,2,3]') == ['a', 1, 2, 3]
    assert json.loads('["a",[1,2],3]') == ['a', [1, 2], 3]


def test_objects():
    assert json.loads('{}') == {}
    assert json.loads('{"a":1}') == {'a': 1}
    assert json.loads('{"a":1,"b":2}') == {'a': 1, 'b': 2}


def test_whitespace():
    source = ' { "a" : 1 , "b" : [ 2 , 3 ] } '
    assert json.loads(source) == {'a': 1, 'b': [2, 3]}
