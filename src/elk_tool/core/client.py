"""Elasticsearch client module."""

import logging
from typing import Any, cast

import requests

from elk_tool.core.credentials import ApiKeyAuth, get_elasticsearch_client
from elk_tool.core.exceptions import ConnectionError, DocumentNotFoundError

log = logging.getLogger(__name__)

# Stream name to index pattern mapping
STREAM_INDICES = {
    "logs": "logs-generic.otel-default",
    "metrics": "metrics-*",
}

# Severity levels (OTel standard)
SEVERITY_LEVELS = {
    "trace": 1,
    "debug": 5,
    "info": 9,
    "warn": 13,
    "error": 17,
    "fatal": 21,
}

# OpenTelemetry resource attribute field names
FIELD_HOST_NAME = "resource.attributes.host.name"
FIELD_SERVICE_NAME = "resource.attributes.service.name"
FIELD_CONTAINER_NAME = "resource.attributes.container.name"


def get_stream_index(stream: str) -> str:
    return STREAM_INDICES.get(stream, stream)


class ElkClient:
    """HTTP client for Elasticsearch operations."""

    DEFAULT_TIMEOUT = 30

    def __init__(self, elk_url: str, auth: ApiKeyAuth) -> None:
        self.elk_url = elk_url
        self.auth = auth

    @classmethod
    def from_environment(cls, profile: str | None = None) -> "ElkClient":
        elk_url, auth = get_elasticsearch_client(profile=profile)
        return cls(elk_url, auth)

    def _execute_request(
        self,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,
        check_status: bool = True,
    ) -> requests.Response:
        """Raises ConnectionError if request fails."""
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                json=json,
                verify=True,
                timeout=self.DEFAULT_TIMEOUT,
            )
            if check_status:
                response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise ConnectionError(f"Request failed: {e}") from e

    def resolve_index(self, index_pattern: str, doc_id: str) -> str:
        """Raises DocumentNotFoundError or ConnectionError."""
        if "*" not in index_pattern:
            return index_pattern

        # Search for the document to get its actual index
        url = f"{self.elk_url}/{index_pattern}/_search"
        body = {"query": {"ids": {"values": [doc_id]}}, "size": 1}
        log.debug("Resolving index pattern %s for document %s", index_pattern, doc_id)

        response = self._execute_request("POST", url, json=body)

        data: dict[str, Any] = response.json()
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            raise DocumentNotFoundError(index_pattern, doc_id)

        return cast(str, hits[0]["_index"])

    def get_document(self, index: str, doc_id: str) -> dict[str, Any]:
        """Raises DocumentNotFoundError or ConnectionError."""
        # Resolve wildcard patterns to actual index
        actual_index = self.resolve_index(index, doc_id)

        url = f"{self.elk_url}/{actual_index}/_doc/{doc_id}"
        log.debug("Fetching document %s from index %s", doc_id, actual_index)

        response = self._execute_request("GET", url, check_status=False)
        if response.status_code == 404:
            raise DocumentNotFoundError(actual_index, doc_id)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ConnectionError(f"Failed to fetch document: {e}") from e

        return cast(dict[str, Any], response.json())

    def delete_document(self, index: str, doc_id: str) -> bool:
        """Returns True if deleted, False if not found. Raises ConnectionError."""
        # Resolve wildcard patterns to actual index
        try:
            actual_index = self.resolve_index(index, doc_id)
        except DocumentNotFoundError:
            log.debug("Document %s not found in index %s", doc_id, index)
            return False

        url = f"{self.elk_url}/{actual_index}/_doc/{doc_id}"
        log.debug("Deleting document %s from index %s", doc_id, actual_index)

        response = self._execute_request("DELETE", url, check_status=False)
        if response.status_code == 404:
            log.debug("Document %s not found during delete", doc_id)
            return False

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ConnectionError(f"Failed to delete document: {e}") from e

        return True

    def search_documents(
        self,
        index: str,
        size: int = 10,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Raises ConnectionError."""
        url = f"{self.elk_url}/{index}/_search"

        body: dict[str, Any] = {"size": size, "sort": [{"@timestamp": {"order": "desc"}}]}

        if query:
            body["query"] = query
        else:
            body["query"] = {"match_all": {}}

        response = self._execute_request("POST", url, json=body)
        return cast(dict[str, Any], response.json())

    def raw_query(
        self,
        index: str,
        query_body: dict[str, Any],
        size: int = 10,
    ) -> dict[str, Any]:
        """Raises ConnectionError."""
        url = f"{self.elk_url}/{index}/_search?size={size}"

        response = self._execute_request("POST", url, json=query_body)
        return cast(dict[str, Any], response.json())

    def list_indices(self, pattern: str = "*") -> list[dict[str, Any]]:
        url = (
            f"{self.elk_url}/_cat/indices/{pattern}?format=json&h=index,health,status,docs.count,store.size"
        )
        response = self._execute_request("GET", url)
        return cast(list[dict[str, Any]], response.json())

    def list_data_streams(self, pattern: str = "*") -> list[dict[str, Any]]:
        url = f"{self.elk_url}/_data_stream/{pattern}"
        response = self._execute_request("GET", url, check_status=False)

        if response.status_code == 404:
            return []

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ConnectionError(f"Failed to list data streams: {e}") from e

        data: dict[str, Any] = response.json()
        return cast(list[dict[str, Any]], data.get("data_streams", []))

    def aggregate_field(
        self,
        index: str,
        field: str,
        size: int = 1000,
        query: dict[str, Any] | None = None,
        time_range: str | None = None,
    ) -> list[dict[str, Any]]:
        """time_range: ELK-style like "15m", "1h", "24h", "7d"."""
        url = f"{self.elk_url}/{index}/_search"

        body: dict[str, Any] = {
            "size": 0,
            "aggs": {
                "unique_values": {
                    "terms": {
                        "field": field,
                        "size": size,
                    }
                }
            },
        }

        # Build query with optional filters
        filters = []
        if query:
            filters.append(query)
        if time_range:
            filters.append({"range": {"@timestamp": {"gte": f"now-{time_range}"}}})

        if filters:
            if len(filters) == 1:
                body["query"] = filters[0]
            else:
                body["query"] = {"bool": {"filter": filters}}

        response = self._execute_request("POST", url, json=body)

        data: dict[str, Any] = response.json()
        buckets = data.get("aggregations", {}).get("unique_values", {}).get("buckets", [])
        return cast(list[dict[str, Any]], buckets)

    def get_mapping(self, index: str) -> dict[str, Any]:
        url = f"{self.elk_url}/{index}/_mapping"
        response = self._execute_request("GET", url)
        return cast(dict[str, Any], response.json())

    def get_cluster_health(self) -> dict[str, Any]:
        url = f"{self.elk_url}/_cluster/health"
        response = self._execute_request("GET", url)
        return cast(dict[str, Any], response.json())

    def get_cluster_nodes(self) -> list[dict[str, Any]]:
        url = f"{self.elk_url}/_cat/nodes?format=json&h=name,ip,heap.percent,ram.percent,cpu,load_1m,node.role,master"
        response = self._execute_request("GET", url)
        return cast(list[dict[str, Any]], response.json())

    def get_unassigned_shards(self) -> list[dict[str, Any]]:
        url = f"{self.elk_url}/_cat/shards?format=json&h=index,shard,prirep,state,unassigned.reason,unassigned.at,unassigned.for"
        response = self._execute_request("GET", url)
        shards: list[dict[str, Any]] = response.json()
        return [s for s in shards if s.get("state") == "UNASSIGNED"]

    def get_allocation_explain(self) -> dict[str, Any]:
        url = f"{self.elk_url}/_cluster/allocation/explain"
        response = self._execute_request("GET", url, check_status=False)

        if response.status_code == 400:
            return {"message": "No unassigned shards to explain"}

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ConnectionError(f"Failed to get allocation explanation: {e}") from e

        return cast(dict[str, Any], response.json())

    def search_logs(
        self,
        index: str,
        size: int = 20,
        host: str | None = None,
        service: str | None = None,
        container: str | None = None,
        min_severity: int | None = None,
        search_text: str | None = None,
        time_range: str | None = None,
        sort_field: str = "@timestamp",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """time_range: ELK-style like "15m", "1h", "24h", "7d", "2w", "1M"."""
        url = f"{self.elk_url}/{index}/_search"

        filters: list[dict[str, Any]] = []

        if host:
            filters.append({"term": {FIELD_HOST_NAME: host}})

        if service:
            filters.append({"term": {FIELD_SERVICE_NAME: service}})

        if container:
            filters.append({"term": {FIELD_CONTAINER_NAME: container}})

        if min_severity is not None:
            filters.append({"range": {"severity_number": {"gte": min_severity}}})

        if time_range:
            filters.append({"range": {"@timestamp": {"gte": f"now-{time_range}"}}})

        if search_text:
            filters.append(
                {
                    "multi_match": {
                        "query": search_text,
                        "fields": [
                            "body",
                            "message",
                            "attributes.message",
                            "attributes.original_message",
                        ],
                    }
                }
            )

        body: dict[str, Any] = {
            "size": size,
            "sort": [{sort_field: {"order": sort_order}}],
        }

        if filters:
            body["query"] = {"bool": {"filter": filters}}
        else:
            body["query"] = {"match_all": {}}

        response = self._execute_request("POST", url, json=body)
        return cast(dict[str, Any], response.json())
