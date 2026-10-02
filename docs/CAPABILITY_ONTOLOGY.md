# Capability Ontology

Namespace (default; override via `CAPABILITY_KG__NAMESPACE`):

```text
https://loanops.local/ontology/
```

Prefix in Turtle: `loanops:`.

## Classes

| Class | Meaning |
|---|---|
| `Capability` | Business-facing capability an agent may invoke |
| `BusinessDomain` | e.g. Loan Servicing |
| `Application` | SSE / enterprise app (e.g. LoanServices) |
| `MCPServer` | MCP server that exposes capabilities |
| `API` | API surface |
| `APIOperation` | OpenAPI / static-extracted operation |
| `Permission` | Authz atom (e.g. loan.read) or role policy name |
| `Role` | Role that may use a capability |
| `Principal` | User/service principal (optional) |
| `Documentation` | Doc pointer |
| `Repository` | Source repo pointer |
| `ReviewStatus` | Governance state (as literal or typed resource) |
| `Enterprise` | Tenant / company root (v2) |
| `Deployable` | Deployable unit inside a repository (v2) |
| `ApiSurface` | HTTP API host surface (v2) |
| `CodeUnit` | Class/method implementing an operation (v2) |
| `DataStore` | Database / catalog (v2) |
| `EventTopic` | SNS/SQS topic (v2) |
| `SdkPackage` | Published NuGet/npm package (v2) |
| `AuthProvider` | Auth0 / AppAuth (v2) |
| `CrossAppRelationship` | First-class cross-app edge (v2) |
| `Evidence` | Provenance node (v2) |
| `Proposal` | LLM semantic overlay pending review (v2) |

## Predicates

| Predicate | Domain → Range |
|---|---|
| `hasDomain` | Capability → BusinessDomain |
| `implementedBy` | Capability → APIOperation |
| `implementedByCodeUnit` | APIOperation → CodeUnit |
| `exposedBy` | Capability → MCPServer |
| `requiresPermission` | Capability → Permission |
| `availableTo` | Capability → Role |
| `dependsOn` | Capability → Capability |
| `relatedTo` | Capability → Capability |
| `documentedBy` | Capability → Documentation |
| `derivedFrom` | Capability → Application / Documentation |
| `reviewedBy` | Capability → Principal |
| `hasReviewStatus` | Capability / CrossAppRelationship → literal status |
| `belongsToApp` | APIOperation → Application |
| `belongsToRepository` | Application → Repository |
| `operationId` | APIOperation → literal |
| `httpMethod` | APIOperation → literal |
| `httpPath` | APIOperation → literal |
| `authzSource` | APIOperation → `attribute` \| `class-level` \| `convention` \| `unknown` |
| `readOnly` | Capability → boolean |
| `intent` | Capability → literal |
| `examples` | Capability → literal |
| `confidence` | Capability / Evidence / CrossAppRelationship → decimal |
| `version` | Capability → literal |
| `source` | Capability → literal |
| `hasEvidence` | Capability / CrossAppRelationship → Evidence |
| `relationshipKind` | CrossAppRelationship → kind literal |
| `fromApplication` / `toApplication` | CrossAppRelationship → Application |
| `toOperation` / `toPackage` / `toTopic` / `toDataStore` / `toAuthProvider` | CrossAppRelationship → literal |
| `repositoryId` / `commitSha` / `filePath` / `lineStart` / `lineEnd` | Evidence → literal |
| `detectorId` / `detectorVersion` / `extractedAt` | Evidence → literal |

Also use `rdf:type`, `rdfs:label`, `rdfs:comment`.

## CrossAppRelationship kinds

`callsOperation` | `callsApplication` | `consumesSdk` | `sharesDto` | `publishesEvent` | `subscribesEvent` | `readsDataStore` | `ownsDataStore` | `authenticatesVia` | `overlapsCapability`

A `CrossAppRelationship` without `hasEvidence` is invalid and must be dropped at write time.

## Review status literals

`discovered` | `enriched` | `pending_review` | `approved` | `rejected` | `deprecated`

## Example (conceptual)

```turtle
@prefix loanops: <https://loanops.local/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

loanops:cap_get_loan_summary a loanops:Capability ;
    rdfs:label "get_loan_summary" ;
    rdfs:comment "Retrieve summary for a mortgage loan." ;
    loanops:hasDomain loanops:domain_loan_servicing ;
    loanops:implementedBy loanops:op_getLoanSummary ;
    loanops:requiresPermission loanops:perm_loan_read ;
    loanops:readOnly true ;
    loanops:hasReviewStatus "discovered" ;
    loanops:exposedBy loanops:mcp_loanops .
```
