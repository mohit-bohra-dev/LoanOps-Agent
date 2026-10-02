"""Ontology terms for the LoanOps capability knowledge graph (v1 + v2)."""

from __future__ import annotations

from rdflib import Namespace

DEFAULT_NAMESPACE = "https://loanops.local/ontology/"


def loanops_ns(base: str = DEFAULT_NAMESPACE) -> Namespace:
    normalized = base if base.endswith("/") or base.endswith("#") else f"{base}/"
    return Namespace(normalized)


# Local names (append to Namespace) — v1
CLASS_CAPABILITY = "Capability"
CLASS_DOMAIN = "BusinessDomain"
CLASS_APPLICATION = "Application"
CLASS_MCP_SERVER = "MCPServer"
CLASS_API = "API"
CLASS_API_OPERATION = "APIOperation"
CLASS_PERMISSION = "Permission"
CLASS_ROLE = "Role"
CLASS_PRINCIPAL = "Principal"
CLASS_DOCUMENTATION = "Documentation"
CLASS_REPOSITORY = "Repository"
CLASS_REVIEW_STATUS = "ReviewStatus"

# v2 enterprise / multi-repo (ADR-015)
CLASS_ENTERPRISE = "Enterprise"
CLASS_DEPLOYABLE = "Deployable"
CLASS_API_SURFACE = "ApiSurface"
CLASS_CODE_UNIT = "CodeUnit"
CLASS_DATA_STORE = "DataStore"
CLASS_EVENT_TOPIC = "EventTopic"
CLASS_SDK_PACKAGE = "SdkPackage"
CLASS_AUTH_PROVIDER = "AuthProvider"
CLASS_CROSS_APP_RELATIONSHIP = "CrossAppRelationship"
CLASS_EVIDENCE = "Evidence"
CLASS_PROPOSAL = "Proposal"

PRED_HAS_DOMAIN = "hasDomain"
PRED_IMPLEMENTED_BY = "implementedBy"
PRED_EXPOSED_BY = "exposedBy"
PRED_REQUIRES_PERMISSION = "requiresPermission"
PRED_AVAILABLE_TO = "availableTo"
PRED_DEPENDS_ON = "dependsOn"
PRED_RELATED_TO = "relatedTo"
PRED_DOCUMENTED_BY = "documentedBy"
PRED_DERIVED_FROM = "derivedFrom"
PRED_REVIEWED_BY = "reviewedBy"
PRED_BELONGS_TO_APP = "belongsToApp"
PRED_OPERATION_ID = "operationId"
PRED_HTTP_METHOD = "httpMethod"
PRED_HTTP_PATH = "httpPath"
PRED_READ_ONLY = "readOnly"
PRED_INTENT = "intent"
PRED_EXAMPLES = "examples"
PRED_REVIEW_STATUS = "hasReviewStatus"
PRED_SOURCE = "source"
PRED_CONFIDENCE = "confidence"
PRED_VERSION = "version"

# v2 predicates
PRED_HAS_EVIDENCE = "hasEvidence"
PRED_IMPLEMENTED_BY_CODE_UNIT = "implementedByCodeUnit"
PRED_BELONGS_TO_REPO = "belongsToRepository"
PRED_HAS_DEPLOYABLE = "hasDeployable"
PRED_HAS_API_SURFACE = "hasApiSurface"
PRED_RELATIONSHIP_KIND = "relationshipKind"
PRED_FROM_APP = "fromApplication"
PRED_TO_APP = "toApplication"
PRED_TO_OPERATION = "toOperation"
PRED_TO_PACKAGE = "toPackage"
PRED_TO_TOPIC = "toTopic"
PRED_TO_DATASTORE = "toDataStore"
PRED_TO_AUTH = "toAuthProvider"
PRED_AUTHZ_SOURCE = "authzSource"
PRED_REPO_ID = "repositoryId"
PRED_COMMIT_SHA = "commitSha"
PRED_FILE_PATH = "filePath"
PRED_LINE_START = "lineStart"
PRED_LINE_END = "lineEnd"
PRED_DETECTOR_ID = "detectorId"
PRED_DETECTOR_VERSION = "detectorVersion"
PRED_EXTRACTED_AT = "extractedAt"
PRED_PACKAGE_ID = "packageId"
PRED_TOPIC_NAME = "topicName"
PRED_CONN_KEY = "connectionKey"
PRED_SERVICE_URL_KEY = "serviceUrlKey"
PRED_HOSTS = "hosts"

# CrossAppRelationship kinds
KIND_CALLS_OPERATION = "callsOperation"
KIND_CALLS_APPLICATION = "callsApplication"
KIND_CONSUMES_SDK = "consumesSdk"
KIND_SHARES_DTO = "sharesDto"
KIND_PUBLISHES_EVENT = "publishesEvent"
KIND_SUBSCRIBES_EVENT = "subscribesEvent"
KIND_READS_DATASTORE = "readsDataStore"
KIND_OWNS_DATASTORE = "ownsDataStore"
KIND_AUTHENTICATES_VIA = "authenticatesVia"
KIND_OVERLAPS_CAPABILITY = "overlapsCapability"

RELATIONSHIP_KINDS = frozenset(
    {
        KIND_CALLS_OPERATION,
        KIND_CALLS_APPLICATION,
        KIND_CONSUMES_SDK,
        KIND_SHARES_DTO,
        KIND_PUBLISHES_EVENT,
        KIND_SUBSCRIBES_EVENT,
        KIND_READS_DATASTORE,
        KIND_OWNS_DATASTORE,
        KIND_AUTHENTICATES_VIA,
        KIND_OVERLAPS_CAPABILITY,
    }
)

AUTHZ_SOURCES = frozenset({"attribute", "class-level", "convention", "unknown"})
