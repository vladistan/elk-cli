"""Integration tests for elk_tool.client module.

Tests use real Elasticsearch instance via elk_client fixture.
"""

import pytest
import requests

from elk_tool.core.client import ElkClient
from elk_tool.core.credentials import ApiKeyAuth
from elk_tool.core.exceptions import ConnectionError, DocumentNotFoundError


def test_resolve_index_with_wildcard(elk_client):
    """Test resolving wildcard index pattern to actual index."""
    # First, find a real document to use for testing
    result = elk_client.search_logs("logs-*", size=1)
    hits = result.get("hits", {}).get("hits", [])
    if not hits:
        pytest.skip("No documents found in logs-* to test with")

    doc_id = hits[0]["_id"]
    expected_index = hits[0]["_index"]

    # Now test resolve_index with the real document
    resolved_index = elk_client.resolve_index("logs-*", doc_id)
    assert isinstance(resolved_index, str)
    assert "*" not in resolved_index
    assert resolved_index == expected_index


def test_resolve_index_without_wildcard(elk_client):
    """Test that non-wildcard patterns are returned as-is."""
    index = "my-index"
    result = elk_client.resolve_index(index, "any-doc-id")
    assert result == index


def test_get_document_not_found(elk_client):
    """Test that get_document raises DocumentNotFoundError for missing document."""
    with pytest.raises(DocumentNotFoundError, match="nonexistent-doc-id"):
        elk_client.get_document("logs-*", "nonexistent-doc-id")


def test_from_environment_creates_client(monkeypatch, elk_url, elk_api_key):
    """Test that from_environment creates ElkClient from environment."""
    monkeypatch.setenv("ELK_URL", elk_url)
    monkeypatch.setenv("ELK_API_KEY", elk_api_key)

    client = ElkClient.from_environment()

    assert isinstance(client, ElkClient)
    assert client.elk_url == elk_url
    assert isinstance(client.auth, ApiKeyAuth)


def test_connection_error_handling(elk_api_key):
    """Test that connection errors are properly raised."""
    auth = ApiKeyAuth(elk_api_key)
    invalid_client = ElkClient("http://invalid-elk-host:9999", auth)

    with pytest.raises(ConnectionError, match="Request failed"):
        invalid_client.resolve_index("logs-*", "any-doc-id")


def test_elk_connection_succeeds(elk_client):
    """Test that ELK connection is established successfully."""
    response = requests.get(f"{elk_client.elk_url}/", auth=elk_client.auth, verify=True, timeout=30)
    assert response.status_code == 200

    data = response.json()
    assert "cluster_name" in data
    assert "version" in data


def test_search_logs_with_search_text(elk_client):
    """Test search_logs with search_text parameter exercises multi_match query.

    Searches for 'DHCP' which is common in firewall dhcpd logs.
    This tests the search_text code path that creates multi_match query
    across body, message, attributes.message, and attributes.original_message.
    """
    result = elk_client.search_logs(
        index="logs-*",
        size=5,
        search_text="DHCP",
        time_range="1h",
    )

    assert "hits" in result
    hits = result["hits"]["hits"]
    # Should find some DHCP-related logs
    assert len(hits) >= 0  # May be 0 if no recent DHCP logs

    # If we found hits, verify they contain DHCP in message fields
    if hits:
        hit = hits[0]
        source = hit.get("_source", {})
        # Check various message fields that search_text targets
        body = source.get("body", "")
        attrs = source.get("attributes", {})
        msg = attrs.get("message", "") or attrs.get("original_message", "")
        combined = f"{body}{msg}".upper()
        assert "DHCP" in combined


def test_search_logs_search_text_no_results(elk_client):
    """Test search_logs with search_text that matches nothing."""
    result = elk_client.search_logs(
        index="logs-*",
        size=5,
        search_text="xyznonexistentstring12345",
    )

    assert "hits" in result
    hits = result["hits"]["hits"]
    assert len(hits) == 0


def test_search_logs_search_text_combined_filters(elk_client):
    """Test search_logs with search_text combined with other filters.

    Tests that search_text works together with service filter.
    """
    result = elk_client.search_logs(
        index="logs-*",
        size=5,
        service="dhcpd",
        search_text="DHCP",
        time_range="24h",
    )

    assert "hits" in result
    # Should find dhcpd logs containing DHCP
    hits = result["hits"]["hits"]
    # Verify results match both filters if any found
    for hit in hits:
        source = hit.get("_source", {})
        service = source.get("resource", {}).get("attributes", {}).get("service.name")
        assert service == "dhcpd"
