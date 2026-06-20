import pytest
from app.services.extraction.llm_client import LLMClient

def test_llm_client_complete_json_failure():
    client = LLMClient()
    
    # Mock complete to raise an exception
    client.complete = lambda sys, user: "invalid json {"
    
    with pytest.raises(RuntimeError) as exc_info:
        client.complete_json("sys", "user")
        
    assert "Failed to parse LLM response as JSON" in str(exc_info.value)
