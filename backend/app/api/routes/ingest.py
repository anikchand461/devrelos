"""
/api/ingest — OpenAPI Spec Ingestion Route
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.parsers.openapi_parser import OpenAPIParser
from app.services.vector_store import VectorStore
from app.models.schemas import IngestRequest, IngestResponse
from app.models.db_models import APIEndpoint
from app.db.session import get_db

router = APIRouter()


@router.post("/", response_model=IngestResponse)
async def ingest_spec(
    body: IngestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest an OpenAPI specification and index all endpoints for semantic search.

    Accepts either:
    - spec_url: URL to fetch the spec from
    - spec_content: Raw YAML/JSON string

    Example:
        POST /api/ingest
        {
            "api_slug": "stripe",
            "spec_url": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json"
        }
    """
    if not body.spec_url and not body.spec_content:
        raise HTTPException(400, "Provide either spec_url or spec_content")

    parser = OpenAPIParser()
    try:
        if body.spec_url:
            endpoints = await parser.from_url(body.spec_url)
        else:
            endpoints = parser.from_string(body.spec_content)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse spec: {e}")

    # Persist endpoint metadata to PostgreSQL
    for ep in endpoints:
        db_ep = APIEndpoint(
            api_slug=body.api_slug,
            path=ep["path"],
            method=ep["method"],
            summary=ep.get("summary", ""),
            description=ep.get("description", ""),
            parameters=ep.get("parameters", []),
            request_body_schema=ep.get("request_body_schema"),
            response_schema=ep.get("response_schema"),
            auth_required=ep.get("auth_required", True),
            tags=ep.get("tags", []),
        )
        db.add(db_ep)
    await db.commit()

    # Index embeddings in vector DB
    vs: VectorStore = request.app.state.vector_store
    embedding_count = await vs.upsert_endpoints(body.api_slug, endpoints)

    return IngestResponse(
        api_slug=body.api_slug,
        endpoints_indexed=len(endpoints),
        schemas_indexed=sum(1 for e in endpoints if e.get("request_body_schema")),
        embedding_count=embedding_count,
        status="success",
    )
