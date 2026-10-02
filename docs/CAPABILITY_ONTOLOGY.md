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
| `APIOperation` | OpenAPI operation |
| `Permission` | Authz atom (e.g. loan.read) |
| `Role` | Role that may use a capability |
| `Principal` | User/service principal (optional) |
| `Documentation` | Doc pointer |
| `Repository` | Source repo pointer |
| `ReviewStatus` | Governance state (as literal or typed resource) |

## Predicates

| Predicate | Domain → Range |
|---|---|
| `hasDomain` | Capability → BusinessDomain |
| `implementedBy` | Capability → APIOperation |
| `exposedBy` | Capability → MCPServer |
| `requiresPermission` | Capability → Permission |
| `availableTo` | Capability → Role |
| `dependsOn` | Capability → Capability |
| `relatedTo` | Capability → Capability |
| `documentedBy` | Capability → Documentation |
| `derivedFrom` | Capability → Application / Documentation |
| `reviewedBy` | Capability → Principal |
| `hasReviewStatus` | Capability → literal status |
| `belongsToApp` | APIOperation → Application |
| `operationId` | APIOperation → literal |
| `httpMethod` | APIOperation → literal |
| `httpPath` | APIOperation → literal |
| `readOnly` | Capability → boolean |
| `intent` | Capability → literal |
| `examples` | Capability → literal |
| `confidence` | Capability → decimal |
| `version` | Capability → literal |
| `source` | Capability → literal |

Also use `rdf:type`, `rdfs:label`, `rdfs:comment`.

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
