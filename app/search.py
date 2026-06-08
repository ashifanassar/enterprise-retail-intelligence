import time
import uuid
from functools import lru_cache
from typing import Any

from google.cloud import bigquery
from google.cloud import discoveryengine_v1beta as discoveryengine

from app.config import (
    BQ_DATASET,
    DATA_STORE_ID,
    ENGINE_ID,
    LOCATION,
    PROJECT_ID,
    SERVING_CONFIG_ID,
)


search_client = discoveryengine.SearchServiceClient()
bigquery_client = bigquery.Client(project=PROJECT_ID)


def _engine_serving_config() -> str:
    return (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/"
        f"engines/{ENGINE_ID}/servingConfigs/{SERVING_CONFIG_ID}"
    )


def _data_store_serving_config() -> str:
    return (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/"
        f"dataStores/{DATA_STORE_ID}/servingConfigs/{SERVING_CONFIG_ID}"
    )


def _doc_to_product(document: discoveryengine.Document) -> dict[str, Any]:
    data = dict(document.struct_data)
    derived = dict(document.derived_struct_data)

    sku_id = data.get("sku_id") or data.get("id") or document.id
    return {
        "sku_id": sku_id,
        "title": data.get("title") or derived.get("title"),
        "description": data.get("description"),
        "category": data.get("category"),
        "price": data.get("price"),
        "inventory_count": data.get("inventory_count"),
        "brand": data.get("brand"),
        "image_url": data.get("image_url"),
    }


def _search_with_serving_config(query: str, serving_config: str) -> list[dict[str, Any]]:
    response = search_client.search(
        request=discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=10,
        )
    )
    return [_doc_to_product(result.document) for result in response.results]


@lru_cache(maxsize=256)
def _cached_vertex_search(query: str) -> tuple[tuple[tuple[str, Any], ...], ...]:
    try:
        products = _search_with_serving_config(query, _engine_serving_config())
    except Exception:
        products = _search_with_serving_config(query, _data_store_serving_config())

    return tuple(tuple(sorted(product.items())) for product in products)


def _query_inventory(sku_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not sku_ids:
        return {}

    sql = f"""
        SELECT sku_id, title, price, inventory_count, brand, image_url, category
        FROM `{PROJECT_ID}.{BQ_DATASET}.catalog_dim`
        WHERE sku_id IN UNNEST(@sku_ids)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("sku_ids", "STRING", sku_ids)]
    )
    rows = bigquery_client.query(sql, job_config=job_config).result()
    return {
        row.sku_id: {
            "title": row.title,
            "price": row.price,
            "inventory_count": row.inventory_count,
            "brand": row.brand,
            "image_url": row.image_url,
            "category": row.category,
        }
        for row in rows
    }


def _log_search(session_id: str, query: str, results_count: int, latency_ms: int) -> None:
    table = f"{PROJECT_ID}.{BQ_DATASET}.search_logs"
    bigquery_client.insert_rows_json(
        table,
        [
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "session_id": session_id,
                "query": query,
                "results_count": results_count,
                "latency_ms": latency_ms,
                "dlp_triggered": False,
            }
        ],
    )


def search_products(query: str, session_id: str | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    session_id = session_id or str(uuid.uuid4())

    products = [dict(product) for product in _cached_vertex_search(query)]
    inventory = _query_inventory([product["sku_id"] for product in products if product.get("sku_id")])

    grounded_products = []
    for product in products:
        sku_id = product.get("sku_id")
        product.update(inventory.get(sku_id, {}))
        if int(product.get("inventory_count") or 0) > 0:
            grounded_products.append(product)

    latency_ms = int((time.perf_counter() - start) * 1000)
    _log_search(session_id, query, len(grounded_products), latency_ms)

    return {
        "session_id": session_id,
        "query": query,
        "results": grounded_products[:10],
        "total_found": len(grounded_products),
        "latency_ms": latency_ms,
    }
