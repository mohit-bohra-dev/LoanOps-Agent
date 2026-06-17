# Conversation Memory Graph Models

This document defines graph nodes and relationships for conversation memory architecture using Graphify's document→graph methodology.

## Core Entities

### Node: `ConversationSession`
**Properties:**
```python
{
    "node_type": "conversation_session",
    "conversation_id": "c123e456-...",
    "created_at": "2026-06-09T12:00:00Z",
    "status": "active | expired | ended",
    "memory_strategy": "loan_centric",
    "loan_id": "100245",           # Nullable
    "rep_id": "CA-REP-12345",      # Nullable
    "context_retention_count": 3,   # How many messages retained
    "confidence_estimate": 0.87     # Estimated relevance
}
```

**Graph Relationships:**
- `(ConversationSession)-[:USES]->(MemoryStrategy)`
- `(ConversationSession)-[:HAS_CONTEXT]->(Message)` (multiple)
- `(ConversationSession)-[:TARGETS_LOAN]->(LoanSummary)` (nullable)
- `(ConversationSession)-[:INVOLVES_REP]->(RepProfile)` (nullable)
- `(ConversationSession)-[:GENERATED_AUDIT]->(AuditEvent)` (multiple)
- `(ConversationSession)-[:END_RESULT]->(AgentTurnOutput)`

---

### Node: `AgentTurn`
**Represents one complete agent processing cycle (including tool calls)**

**Properties:**
```python
{
    "node_type": "agent_turn",
    "turn_id": "t789...",
    "conversation_id": "c123e456...",
    "timestamp": "2026-06-09T12:05:32Z",
    "intent_type": "answer | refuse | escalate",
    "tools_used": ["lookup_loan", "search_policy"],
    "tool_execution_time_ms": 245,
    "llm_calls": 2,                 # First pass + second pass
    "pii_detected": True,
    "pii_redacted": True,
    "confidence": 0.92,
    "memory_context_referenced_ids": ["m1", "m3", "m5"]
}
```

**Graph Relationships:**
- `(AgentTurn)-[:BELONGS_TO]->(ConversationSession)`
- `(AgentTurn)-[:PROCESSED_MESSAGE]->(Message)` (user input)
- `(AgentTurn)-[:GENERATED_OUTPUT]->(AgentTurnOutput)`
- `(AgentTurn)-[:CALLED_TOOL]->(ToolCall)` (multiple)
- `(AgentTurn)-[:USED_STRATEGY]->(MemoryStrategy)`

---

### Node: `Message` (LLMMessage in code)
**Properties:**
```python
{
    "node_type": "message",
    "message_id": "m1",
    "conversation_id": "c123e456...",
    "role": "system | user | assistant | tool",
    "content_preview": "Loan 100245...",  # Truncated for graph
    "content_hash": "sha256:...",          # Full text indexed separately
    "timestamp": "2026-06-09T12:05:32Z",
    "estimated_tokens": 45,
    "has_pii": False,                      # If True, content encrypted
    "encryption_key_id": "key-vault-id"    # Nullable
}
```

**Graph Relationships:**
- `(Message)-[:PART_OF]->(ConversationSession)`
- `(Message)-[:PREVIOUS]->(Message)` (temporal ordering)
- `(Message)-[:RESPONSE_TO]->(Message)` (when role=assistant/tool)
- `(Message)-[:REFERENCES_LOAN]->(LoanSummary)`
- `(Message)-[:CONTAINS_POLICY_CITATION]->(PolicySnippet)`

---

### Node: `MemoryStrategy`
**Properties (immutable/ENUM-like):**
```python
{
    "node_type": "memory_strategy",
    "strategy_name": "last_n | sliding_window | loan_centric | policy_aware",
    "config_schema": "{max_messages: int} | {max_tokens: int} | ...",
    "context_window_size": "fixed | dynamic | loan_specific | policy_weighted",
    "privacy_level": "high | medium | low"  # How much PII retained
}
```

**Graph Relationships:**
- `(MemoryStrategy)-[:APPLIED_TO]->(ConversationSession)`
- `(MemoryStrategy)-[:CONFIGURED_IN]->(AgentConfig)`
- `(MemoryStrategy)-[:USED_IN_TURN]->(AgentTurn)` (shows adoption rate)

---

### Node: `ContextDecision`
**Represents the memory provider's retention choices per turn**

**Properties:**
```python
{
    "node_type": "context_decision",
    "decision_id": "d1",
    "turn_id": "t789...",
    "strategy": "loan_centric",
    "total_messages_available": 8,
    "messages_retained": 3,
    "retention_reasons": [
        "loan_reference_in_msg_7",
        "policy_citation_in_msg_6",
        "temporal_proximity"
    ],
    "pruned_message_ids": ["m1", "m2", "m4"],
    "tokens_saved": 157,
    "relevance_score": 0.89
}
```

**Graph Relationships:**
- `(ContextDecision)-[:FOR_TURN]->(AgentTurn)`
- `(ContextDecision)-[:KEPT]->(Message)` (multiple)
- `(ContextDecision)-[:DISCARDED]->(Message)` (multiple)
- `(ContextDecision)-[:USED_STRATEGY]->(MemoryStrategy)`

---

### Node: `PolicySnippet` (from citations)
**Properties:**
```python
{
    "node_type": "policy_snippet",
    "source_path": "data/sops/escrow/annual-analysis.md#sec-2",
    "version": "2026.03",
    "word_count": 45,
    "usage_count": 23,  # How many conversations cited this
    "escalation_safe_topic": True  # Whether this snippet avoided escalation
}
```

**Graph Relationships:**
- `(PolicySnippet)-[:CITED_IN]->(Message)`
- `(PolicySnippet)-[:PART_OF_FILE]->(PolicyFile)`
- `(PolicySnippet)-[:PREVENTED_ESCALATION]->(EscalationEvent)` (when relevant)

---

### Node: `EscalationEvent`
**Only created when escalation occurs**

**Properties:**
```python
{
    "node_type": "escalation",
    "escalation_id": "e1",
    "conversation_id": "c123e456...",
    "turn_id": "t789...",
    "category": "safety | complaint_or_regulatory | legal_status | fraud | identity",
    "trigger_phrase": "bankruptcy",
    "memory_context_influenced": False,  # Did memory retention cause this?
    "resolution": "pending | resolved | reviewed_by_supervisor"
}
```

**Graph Relationships:**
- `(EscalationEvent)-[:TRIGGERED_BY]->(Message)`
- `(EscalationEvent)-[:RELATED_TO_TURN]->(AgentTurn)`
- `(EscalationEvent)-[:IN_SESSION]->(ConversationSession)`
- `(EscalationEvent)-[:VIOLATED_POLICY]->(PolicyRequirement)`

---

## Interesting Graph Queries

### 1. Identify Memory Strategy Effectiveness
```javascript
MATCH (s:ConversationSession)-[:USES]->(strategy:MemoryStrategy)
OPTIONAL MATCH (s)-[:HAS_CONTEXT]->(msg:Message)
WITH strategy, s, count(msg) as contextSize, s.context_retention_count as declaredSize
OPTIONAL MATCH (s)-[:END_RESULT]->(output:AgentTurnOutput)
RETURN
  strategy.strategy_name,
  avg(contextSize) as avg_actual_context,
  avg(output.confidence) as avg_confidence,
  count(distinct s) as total_sessions
ORDER BY avg_confidence DESC
```

### 2. Find Conversations Where Memory Prevented Escalation
```javascript
MATCH (s:ConversationSession)-[:HAS_CONTEXT]->(m:Message)
WHERE m.role = "assistant" AND m.content_preview CONTAINS "bankruptcy"
MATCH (s)-[:HAS_CONTEXT]->(m2:Message)
WHERE m2.role = "assistant" AND m2.content_preview CONTAINS "bankruptcy protection options"
// No escalation event should exist
// This query finds conversations that could have escalated but didn't
```

### 3. Context Overlap & Redundancy
```javascript
MATCH (turn:AgentTurn)-[:PROCESSED_MESSAGE]->(currentMsg:Message)
OPTIONAL MATCH (turn)-[:USED->:CONTEXT_DECISION]->(decision:ContextDecision)
WHERE currentMsg.timestamp < decision.timestamp
WITH turn, count(distinct decision.retained_message_ids) as retainedCount
WHERE retainedCount > 5
RETURN turn.turn_id, retainedCount
```

### 4. Memory Impact on Tool Usage
```javascript
MATCH (s:ConversationSession)
WITH s
MATCH (turn1:AgentTurn)-[:BELONGS_TO]->(s)
WHERE turn1.tools_used IS NOT NULL
OPTIONAL MATCH (turn2:AgentTurn)-[:BELONGS_TO]->(s)
WHERE turn2.turn_number > turn1.turn_number AND turn2.tools_used IS NOT NULL
RETURN
  s.memory_strategy,
  avg(size(turn1.tools_used)) as first_turn_tools,
  avg(size(turn2.tools_used)) as later_turn_tools
ORDER BY (later_turn_tools - first_turn_tools) DESC
```

---

## Graph Schema Extensions for Graphify

Add to `graphify-out/graph.json` automatically via AST updates after implementing memory code:

```json
{
    "node_types": [
        {...},
        {
            "name": "ConversationSession",
            "category": "conversation",
            "properties": ["conversation_id", "memory_strategy", "status"]
        }
    ],
    "relationships": [
        {
            "from": "ConversationSession",
            "to": "MemoryStrategy",
            "type": "USES",
            "cardinality": "MANY_TO_ONE"
        },
        {...}
    ]
}
```

---

## Compliance Note

**All conversational nodes with PII must be marked:**
```python
"sensitivity_level": "high",  # When PII present
"contains_pii": True,
"retention_policy": "transient_only",  # Don't persist in graph beyond audit
```

Graph queries must respect retention policy annotations to avoid accidentally surfacing encrypted/purged data.
