"""Pydantic schemas for structured relationship extraction (PRD FR-1.1, FR-1.3)."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, model_validator


class EntityType(str, Enum):
    COMPANY = "Company"
    PERSON = "Person"
    PRODUCT = "Product"
    TECHNOLOGY = "Technology"
    MARKET = "Market"
    LOCATION = "Location"
    REGULATION = "Regulation"


class RelationType(str, Enum):
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    ACQUIRED = "ACQUIRED"
    INVESTS_IN = "INVESTS_IN"
    PARTNERS_WITH = "PARTNERS_WITH"
    SUPPLIES_TO = "SUPPLIES_TO"
    MANUFACTURED_BY = "MANUFACTURED_BY"
    COMPETES_WITH = "COMPETES_WITH"
    OFFERS = "OFFERS"
    BUILT_ON = "BUILT_ON"
    COMPETES_IN = "COMPETES_IN"
    OPERATES_IN = "OPERATES_IN"
    SUBJECT_TO = "SUBJECT_TO"
    OFFICER_OF = "OFFICER_OF"


RELATION_DEFAULT_TARGETS: dict[RelationType, EntityType] = {
    RelationType.SUBSIDIARY_OF: EntityType.COMPANY,
    RelationType.ACQUIRED: EntityType.COMPANY,
    RelationType.INVESTS_IN: EntityType.COMPANY,
    RelationType.PARTNERS_WITH: EntityType.COMPANY,
    RelationType.SUPPLIES_TO: EntityType.COMPANY,
    RelationType.MANUFACTURED_BY: EntityType.COMPANY,
    RelationType.COMPETES_WITH: EntityType.COMPANY,
    RelationType.OFFERS: EntityType.PRODUCT,
    RelationType.BUILT_ON: EntityType.TECHNOLOGY,
    RelationType.COMPETES_IN: EntityType.MARKET,
    RelationType.OPERATES_IN: EntityType.LOCATION,
    RelationType.SUBJECT_TO: EntityType.REGULATION,
    RelationType.OFFICER_OF: EntityType.COMPANY,
}

RELATION_DEFAULT_SOURCES: dict[RelationType, EntityType] = {
    RelationType.SUBSIDIARY_OF: EntityType.COMPANY,
    RelationType.ACQUIRED: EntityType.COMPANY,
    RelationType.INVESTS_IN: EntityType.COMPANY,
    RelationType.PARTNERS_WITH: EntityType.COMPANY,
    RelationType.SUPPLIES_TO: EntityType.COMPANY,
    RelationType.MANUFACTURED_BY: EntityType.PRODUCT,
    RelationType.COMPETES_WITH: EntityType.COMPANY,
    RelationType.OFFERS: EntityType.COMPANY,
    RelationType.BUILT_ON: EntityType.PRODUCT,
    RelationType.COMPETES_IN: EntityType.COMPANY,
    RelationType.OPERATES_IN: EntityType.COMPANY,
    RelationType.SUBJECT_TO: EntityType.COMPANY,
    RelationType.OFFICER_OF: EntityType.PERSON,
}


def _match_entity_type(val: Any) -> EntityType | None:
    if not val or not isinstance(val, str):
        return None
    clean = val.strip().lower()
    for member in EntityType:
        if member.value.lower() == clean:
            return member
    return None


def _match_relation_type(val: Any) -> RelationType | None:
    if not val or not isinstance(val, str):
        return None
    clean = val.strip().upper().replace(" ", "_").replace("-", "_")
    if clean in RelationType.__members__:
        return RelationType[clean]
    return None


class ExtractedRelation(BaseModel):
    head_name: str = Field(..., description="Name of the source entity")
    head_type: EntityType = Field(..., description="Ontology type of the source entity")
    relation: RelationType = Field(..., description="Constrained ontology relationship type")
    tail_name: str = Field(..., description="Name of the target entity")
    tail_type: EntityType = Field(..., description="Ontology type of the target entity")
    evidence_quote: str = Field(
        ...,
        description="Exact verbatim quote from the source chunk text evidencing this relationship",
    )
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Model-reported confidence score between 0.0 and 1.0",
    )
    role: str | None = Field(default=None, description="Optional role/title (e.g., for OFFICER_OF)")
    year: int | None = Field(
        default=None, description="Optional event year (e.g., for ACQUIRED or INVESTS_IN)"
    )

    @model_validator(mode="before")
    @classmethod
    def sanitize_relation_data(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Normalize relation
        rel_obj = _match_relation_type(data.get("relation"))
        if rel_obj:
            data["relation"] = rel_obj

        # Normalize or infer head_type
        head_t = _match_entity_type(data.get("head_type"))
        if not head_t and rel_obj:
            head_t = RELATION_DEFAULT_SOURCES.get(rel_obj, EntityType.COMPANY)
        if head_t:
            data["head_type"] = head_t

        # Normalize or infer tail_type
        tail_t = _match_entity_type(data.get("tail_type"))
        if not tail_t and rel_obj:
            tail_t = RELATION_DEFAULT_TARGETS.get(rel_obj, EntityType.COMPANY)
        if tail_t:
            data["tail_type"] = tail_t

        return data


class ExtractionResult(BaseModel):
    chunk_id: str
    relations: list[ExtractedRelation] = Field(
        default_factory=list,
        description="List of extracted relationships grounded in the source chunk",
    )
