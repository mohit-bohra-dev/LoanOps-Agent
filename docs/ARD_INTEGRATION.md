# ARD Integration (later)

**Status:** Not implemented. Master phase 14.

## Role

ARD (Agent Resource Discovery) answers:

> Which enterprise MCP resource / server should the agent connect to?

It does **not** replace:

- RDF Capability KG (what capabilities exist inside a server)
- MCP (how to invoke a capability)
- Graphify (LoanOps code structure)

## Target shape

```text
ARD
 ↓ discover resources
LoanOps MCP | Customer MCP | Docs MCP
 ↓
CapabilityCatalog / RDF
 ↓
invoke_sse_api / docs
```

## Prerequisites before ARD

1. Stable Streamable HTTP MCP (done)
2. Capability catalog + governance (in progress)
3. Multi-client validation (Cursor / Gemini)
4. Clear resource metadata (URLs, scopes, tenants)

Do not implement ARD as a prerequisite for MCP or RDF v1.
