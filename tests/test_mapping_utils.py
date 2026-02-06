import pytest

from elk_tool.infrastructure.utils import flatten_fields


def test_flatten_fields_simple_properties():
    props = {
        "name": {"type": "text"},
        "age": {"type": "integer"},
        "active": {"type": "boolean"},
    }

    result = flatten_fields(props)

    assert result == [
        ("active", "boolean"),
        ("age", "integer"),
        ("name", "text"),
    ]


def test_flatten_fields_nested_objects():
    props = {
        "user": {
            "properties": {
                "name": {"type": "text"},
                "email": {"type": "keyword"},
            }
        },
        "timestamp": {"type": "date"},
    }

    result = flatten_fields(props)

    assert result == [
        ("timestamp", "date"),
        ("user", "object"),
        ("user.email", "keyword"),
        ("user.name", "text"),
    ]


def test_flatten_fields_deeply_nested():
    props = {
        "attributes": {
            "properties": {
                "net": {
                    "properties": {
                        "host": {
                            "properties": {
                                "name": {"type": "keyword"},
                            }
                        }
                    }
                }
            }
        }
    }

    result = flatten_fields(props)

    assert result == [
        ("attributes", "object"),
        ("attributes.net", "object"),
        ("attributes.net.host", "object"),
        ("attributes.net.host.name", "keyword"),
    ]


def test_flatten_fields_with_prefix():
    props = {
        "name": {"type": "text"},
        "age": {"type": "integer"},
    }

    result = flatten_fields(props, prefix="user.")

    assert result == [
        ("user.age", "integer"),
        ("user.name", "text"),
    ]


def test_flatten_fields_filter_exact_match():
    props = {
        "attributes": {
            "properties": {
                "net": {"type": "keyword"},
                "host": {"type": "keyword"},
            }
        },
        "timestamp": {"type": "date"},
    }

    result = flatten_fields(props, field_filter="attributes.net")

    assert result == [("attributes.net", "keyword")]


def test_flatten_fields_filter_prefix_match():
    props = {
        "attributes": {
            "properties": {
                "net": {
                    "properties": {
                        "host": {"type": "keyword"},
                        "port": {"type": "integer"},
                    }
                },
                "other": {"type": "text"},
            }
        },
        "timestamp": {"type": "date"},
    }

    result = flatten_fields(props, field_filter="attributes.net")

    assert result == [
        ("attributes.net", "object"),
        ("attributes.net.host", "keyword"),
        ("attributes.net.port", "integer"),
    ]


def test_flatten_fields_filter_leaf_field():
    props = {
        "attributes": {
            "properties": {
                "net": {
                    "properties": {
                        "host": {"type": "keyword"},
                    }
                }
            }
        }
    }

    result = flatten_fields(props, field_filter="attributes.net.host")

    assert result == [
        ("attributes.net.host", "keyword"),
    ]


def test_flatten_fields_empty_props():
    result = flatten_fields({})
    assert result == []


def test_flatten_fields_no_type_defaults_to_object():
    props = {
        "custom": {},
    }

    result = flatten_fields(props)

    assert result == [("custom", "object")]


@pytest.mark.parametrize(
    "props,field_filter,expected_count",
    [
        ({"a": {"type": "text"}, "b": {"type": "text"}}, "a", 1),
        ({"a": {"type": "text"}, "b": {"type": "text"}}, "b", 1),
        ({"a": {"type": "text"}, "b": {"type": "text"}}, "c", 0),
        ({"a": {"type": "text"}, "b": {"type": "text"}}, None, 2),
    ],
)
def test_flatten_fields_parametrized_filters(props, field_filter, expected_count):
    result = flatten_fields(props, field_filter=field_filter)
    assert len(result) == expected_count
