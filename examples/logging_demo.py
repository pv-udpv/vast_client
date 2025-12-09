#!/usr/bin/env python3
"""Example demonstrating the new logging architecture with request IDs and aggregation."""

import asyncio
import structlog

from vast_client.logging import (
    LoggingContext,
    VastLoggingConfig,
    SamplingStrategy,
    set_logging_config,
)
from vast_client.log_config import get_context_logger


# Configure structlog for JSON output
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)


async def simulate_trackable_send(trackable_index: int, parent_span_id: str) -> bool:
    """Simulate sending a trackable with nested logging context."""
    logger = get_context_logger("trackable")
    
    async with LoggingContext(
        parent_id=parent_span_id,
        operation="send_trackable",
        trackable={"index": trackable_index, "key": f"imp_{trackable_index}"}
    ) as ctx:
        # Simulate HTTP request
        ctx.set_namespace("http", method="GET", url=f"https://example.com/track/{trackable_index}")
        
        logger.debug("Sending trackable", **ctx.to_log_dict())
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Simulate success
        success = trackable_index % 2 == 0  # Even indices succeed
        ctx.set_namespace("http", status_code=200 if success else 500)
        ctx.result["success"] = success
        ctx.result["duration"] = ctx.get_duration()
        
        if success:
            logger.info("Trackable sent successfully", **ctx.to_log_dict())
        else:
            logger.warning("Trackable send failed", **ctx.to_log_dict())
        
        return success


async def simulate_track_event(event_type: str, creative_id: str, trackables_count: int):
    """Simulate tracking an event with multiple trackables."""
    logger = get_context_logger("tracker")
    
    async with LoggingContext(
        operation="track_event",
        vast_event={"type": event_type, "creative_id": creative_id}
    ) as ctx:
        logger.info("Event tracking started", **ctx.to_log_dict())
        
        # Send all trackables
        results = []
        for i in range(trackables_count):
            success = await simulate_trackable_send(i, ctx.span_id)
            results.append(success)
        
        # Aggregate results
        successful_count = sum(results)
        ctx.result.update({
            "success": successful_count == trackables_count,
            "duration": ctx.get_duration(),
            "successful_trackables": successful_count,
            "total_trackables": trackables_count,
        })
        
        if successful_count == trackables_count:
            logger.info("Event tracked successfully", **ctx.to_log_dict())
        elif successful_count > 0:
            logger.warning("Event tracked partially", **ctx.to_log_dict())
        else:
            logger.error("Event tracking failed completely", **ctx.to_log_dict())


async def main():
    """Main demonstration."""
    print("=" * 80)
    print("VAST Client - Enhanced Logging Architecture Demo")
    print("=" * 80)
    print()
    
    # Configure logging
    print("Configuring logging with:")
    print("  - Debug sample rate: 50% (deterministic)")
    print("  - Operation levels: track_event=INFO, send_trackable=DEBUG")
    print()
    
    config = VastLoggingConfig(
        level="INFO",
        debug_sample_rate=0.5,
        sampling_strategy=SamplingStrategy.DETERMINISTIC,
        operation_levels={
            "track_event": "INFO",
            "send_trackable": "DEBUG",
        },
    )
    set_logging_config(config)
    
    # Simulate multiple tracking events
    print("Simulating 2 tracking events with 3 trackables each...")
    print("=" * 80)
    print()
    
    await simulate_track_event("impression", "creative-001", 3)
    print()
    await simulate_track_event("start", "creative-002", 3)
    
    print()
    print("=" * 80)
    print("Demo complete!")
    print()
    print("Key features demonstrated:")
    print("  ✓ Request ID correlation (all logs from same event share request_id)")
    print("  ✓ Hierarchical context (parent-child via span_id and parent_id)")
    print("  ✓ Namespace aggregation (vast_event, trackable, result, http)")
    print("  ✓ Sampling control (only some debug logs shown based on config)")
    print("  ✓ Operation-level control (track_event always logs, send_trackable conditional)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
