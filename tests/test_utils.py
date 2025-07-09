import pytest
from src.utils import serialize


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        ("Hello World", "Hello-World"),
        ("  leading and trailing spaces  ", "leading-and-trailing-spaces"),
                (r'''Special---Chars!@#$%"..''', "Special-Chars"),
        ("multiple   spaces", "multiple-spaces"),
        ("hyphen--and--spaces", "hyphen-and-spaces"),
        ("", ""),
    ],
)
def test_serialize(input_string, expected_output):
    """Test the serialize static method with various inputs."""
    assert serialize(input_string) == expected_output
