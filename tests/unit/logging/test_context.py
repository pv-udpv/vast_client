"""Tests for LoggingContext."""

import asyncio
import pytest

from vast_client.logging import LoggingContext, get_current_context, clear_context


class TestLoggingContext:
    """Test suite for LoggingContext class."""
    
    def teardown_method(self):
        """Clean up context after each test."""
        clear_context()
    
    def test_context_generates_ids(self):
        """Test that context generates request_id and span_id."""
        ctx = LoggingContext(operation="test_op")
        
        assert ctx.request_id is not None
        assert ctx.span_id is not None
        assert len(ctx.request_id) == 12  # 6 bytes = 12 hex chars
        assert len(ctx.span_id) == 12
    
    def test_context_with_explicit_ids(self):
        """Test context with explicit request_id and span_id."""
        ctx = LoggingContext(
            request_id="abc123def456",
            span_id="xyz789uvw012",
            operation="test_op"
        )
        
        assert ctx.request_id == "abc123def456"
        assert ctx.span_id == "xyz789uvw012"
    
    def test_context_manager(self):
        """Test context manager sets and clears contextvars."""
        with LoggingContext(operation="test_op") as ctx:
            # Inside context - should be retrievable
            current = get_current_context()
            assert current is not None
            assert current.request_id == ctx.request_id
            assert current.operation == "test_op"
        
        # Outside context - should be None
        current = get_current_context()
        assert current is None
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager."""
        async with LoggingContext(operation="async_op") as ctx:
            current = get_current_context()
            assert current is not None
            assert current.request_id == ctx.request_id
            assert current.operation == "async_op"
        
        current = get_current_context()
        assert current is None
    
    def test_nested_contexts(self):
        """Test nested contexts with parent-child relationships."""
        with LoggingContext(operation="parent_op") as parent_ctx:
            parent_span_id = parent_ctx.span_id
            
            # Nested context should inherit request_id and set parent_id
            with LoggingContext(operation="child_op") as child_ctx:
                assert child_ctx.request_id == parent_ctx.request_id
                assert child_ctx.parent_id == parent_span_id
                assert child_ctx.span_id != parent_ctx.span_id
    
    @pytest.mark.asyncio
    async def test_async_propagation(self):
        """Test context propagation across async calls."""
        async def nested_operation():
            """Nested async function that should inherit context."""
            current = get_current_context()
            assert current is not None
            assert current.operation == "root_op"
            return current.request_id
        
        async with LoggingContext(operation="root_op") as root_ctx:
            request_id = await nested_operation()
            assert request_id == root_ctx.request_id
    
    @pytest.mark.asyncio
    async def test_async_tasks_inherit_context(self):
        """Test that asyncio tasks inherit context."""
        async def task_function():
            """Task that should inherit parent context."""
            current = get_current_context()
            return current.request_id if current else None
        
        async with LoggingContext(operation="parent") as ctx:
            # Create task in context - should inherit
            task = asyncio.create_task(task_function())
            task_request_id = await task
            
            assert task_request_id == ctx.request_id
    
    def test_namespace_grouping(self):
        """Test namespace grouping for aggregated logging."""
        ctx = LoggingContext(operation="track_event")
        
        # Set fields in built-in namespaces
        ctx.vast_event = {"type": "impression", "creative_id": "123"}
        ctx.trackable = {"index": 0, "key": "imp_0"}
        ctx.result = {"success": True, "duration": 0.123}
        
        log_dict = ctx.to_log_dict()
        
        assert "vast_event" in log_dict
        assert log_dict["vast_event"]["type"] == "impression"
        assert log_dict["vast_event"]["creative_id"] == "123"
        
        assert "trackable" in log_dict
        assert log_dict["trackable"]["index"] == 0
        
        assert "result" in log_dict
        assert log_dict["result"]["success"] is True
    
    def test_custom_namespace(self):
        """Test custom namespace support."""
        ctx = LoggingContext(operation="test")
        
        # Set custom namespace fields
        ctx.set_namespace("http", method="GET", status_code=200)
        ctx.set_namespace("config", timeout=5.0, retries=3)
        
        log_dict = ctx.to_log_dict()
        
        assert "http" in log_dict
        assert log_dict["http"]["method"] == "GET"
        assert log_dict["http"]["status_code"] == 200
        
        assert "config" in log_dict
        assert log_dict["config"]["timeout"] == 5.0
    
    def test_get_namespace(self):
        """Test getting namespace fields."""
        ctx = LoggingContext(operation="test")
        ctx.vast_event = {"type": "start"}
        ctx.set_namespace("custom", field1="value1")
        
        event_ns = ctx.get_namespace("vast_event")
        assert event_ns["type"] == "start"
        
        custom_ns = ctx.get_namespace("custom")
        assert custom_ns["field1"] == "value1"
        
        # Non-existent namespace
        empty_ns = ctx.get_namespace("nonexistent")
        assert empty_ns == {}
    
    def test_to_log_dict_excludes_none(self):
        """Test that to_log_dict excludes None values appropriately."""
        # Root context without parent_id
        ctx = LoggingContext(operation="root")
        log_dict = ctx.to_log_dict()
        
        assert "request_id" in log_dict
        assert "span_id" in log_dict
        assert "operation" in log_dict
        assert "parent_id" not in log_dict  # Should not include None parent_id
    
    def test_to_log_dict_includes_parent_id(self):
        """Test that to_log_dict includes parent_id when present."""
        with LoggingContext(operation="parent") as parent_ctx:
            with LoggingContext(operation="child") as child_ctx:
                log_dict = child_ctx.to_log_dict()
                
                assert "parent_id" in log_dict
                assert log_dict["parent_id"] == parent_ctx.span_id
    
    def test_get_duration(self):
        """Test duration tracking."""
        import time
        
        ctx = LoggingContext(operation="test")
        time.sleep(0.01)  # Sleep 10ms
        
        duration = ctx.get_duration()
        assert duration >= 0.01
        assert duration < 1.0  # Should be less than 1 second
    
    def test_clear_context(self):
        """Test clearing context."""
        with LoggingContext(operation="test"):
            assert get_current_context() is not None
        
        # Context should be cleared after exiting
        assert get_current_context() is None
        
        # Manually set context
        with LoggingContext(operation="manual"):
            pass
        
        # Explicitly clear
        clear_context()
        assert get_current_context() is None
    
    def test_multiple_nested_levels(self):
        """Test multiple levels of nesting."""
        with LoggingContext(operation="level1") as ctx1:
            with LoggingContext(operation="level2") as ctx2:
                with LoggingContext(operation="level3") as ctx3:
                    # All should share same request_id
                    assert ctx1.request_id == ctx2.request_id == ctx3.request_id
                    
                    # Parent-child relationships
                    assert ctx2.parent_id == ctx1.span_id
                    assert ctx3.parent_id == ctx2.span_id
                    
                    # Different span_ids
                    assert ctx1.span_id != ctx2.span_id != ctx3.span_id
