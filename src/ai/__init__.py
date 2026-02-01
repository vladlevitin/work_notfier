"""AI module - OpenAI-powered post analysis and categorization."""

from .ai_processor import process_post_with_ai, should_process_with_ai, is_service_request

__all__ = ['process_post_with_ai', 'should_process_with_ai', 'is_service_request']
