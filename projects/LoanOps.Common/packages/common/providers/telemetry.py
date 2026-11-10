"""Telemetry provider protocol — re-exports from provider_contracts."""

from provider_contracts.telemetry import AbstractTelemetryProvider as TelemetryProvider
from provider_contracts.telemetry import (
    BufferedSpan,
    SpanContext,
    SpanKind,
    begin_trace_collection,
    current_span_context,
    drain_trace_spans,
    record_completed_span,
    trace_span,
)

__all__ = [
    "BufferedSpan",
    "SpanContext",
    "SpanKind",
    "TelemetryProvider",
    "begin_trace_collection",
    "current_span_context",
    "drain_trace_spans",
    "record_completed_span",
    "trace_span",
]
