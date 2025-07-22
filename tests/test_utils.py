from app.utils import serialize

def test_serialize():
    assert serialize("Test String") == "Test-String"
    assert serialize("  leading and trailing spaces  ") == "leading-and-trailing-spaces"
    assert serialize("!@#$%^&*()_+") == ""
    assert serialize("a-b-c") == "a-b-c"