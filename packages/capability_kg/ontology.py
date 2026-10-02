"""Ontology terms for the LoanOps capability knowledge graph."""

from __future__ import annotations

from rdflib import Namespace


DEFAULT_NAMESPACE = "https://loanops.local/ontology/"


def loanops_ns(base: str = DEFAULT_NAMESPACE) -> Namespace:
    normalized = base if base.endswith("/") or base.endswith("#") else f"{base}/"
    return Namespace(normalized)


# Local names (append to Namespace)
CLASS_CAPABILITY = "Capability"
CLASS_DOMAIN = "BusinessDomain"
CLASS_APPLICATION = "Application"
CLASS_MCP_SERVER = "MCPServer"
CLASS_API = "API"
CLASS_API_OPERATION = "APIOperation"
CLASS_PERMISSION = "Permission"
CLASS_ROLE = "Role"

PRED_HAS_DOMAIN = "hasDomain"
PRED_IMPLEMENTED_BY = "implementedBy"
PRED_EXPOSED_BY = "exposedBy"
PRED_REQUIRES_PERMISSION = "requiresPermission"
PRED_AVAILABLE_TO = "availableTo"
PRED_DEPENDS_ON = "dependsOn"
PRED_BELONGS_TO_APP = "belongsToApp"
PRED_OPERATION_ID = "operationId"
PRED_HTTP_METHOD = "httpMethod"
PRED_HTTP_PATH = "httpPath"
PRED_READ_ONLY = "readOnly"
PRED_INTENT = "intent"
PRED_REVIEW_STATUS = "hasReviewStatus"
PRED_SOURCE = "source"
PRED_CONFIDENCE = "confidence"
PRED_VERSION = "version"
