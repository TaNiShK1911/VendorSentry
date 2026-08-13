import json
import logging
from typing import List, Dict, Any

from app.core.config import Settings
from app.models.vendor import Vendor
from app.models.vendor_score import VendorScore

logger = logging.getLogger(__name__)

def _get_groq_client():
    try:
        from groq import Groq
        s = Settings()
        key = s.groq_api_key
        if not key:
            return None
        return Groq(api_key=key)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None

def generate_onboarding_tasks(vendor: Vendor, latest_score: VendorScore | None) -> List[Dict[str, str]]:
    """
    Generate dynamic onboarding tasks based on the vendor's risk profile using an LLM.
    Returns a list of dicts: [{"title": "...", "description": "..."}]
    """
    client = _get_groq_client()
    
    # Fallback default tasks if LLM is unavailable
    default_tasks = [
        {"title": "Sign NDA", "description": "Standard Non-Disclosure Agreement."},
        {"title": "Security Questionnaire", "description": "Complete the standard security assessment."}
    ]
    
    if latest_score and latest_score.tier in ["HIGH", "CRITICAL"]:
        default_tasks.append({"title": "Sign DPA", "description": "Data Processing Agreement is required for high-risk vendors."})
        default_tasks.append({"title": "Provide SOC2 Type II", "description": "Latest SOC2 report must be provided and reviewed."})

    if not client:
        return default_tasks

    prompt = f"""
    You are an expert third-party vendor risk analyst.
    Please generate an onboarding checklist for the following vendor:
    Name: {vendor.name}
    Type: {vendor.vendor_type}
    Risk Tier: {latest_score.tier if latest_score else 'Unknown'}
    Anomalies: {", ".join(latest_score.anomaly_types) if latest_score and latest_score.anomaly_types else 'None'}
    
    Return ONLY a JSON array of objects, where each object has two string fields: 'title' and 'description'.
    The tasks should be specific and tailored to the vendor's risk profile (e.g., if they have a breach history, require a breach remediation report. If they have high risk, require SOC2/DPA). Limit to 4-5 tasks.
    Do NOT return any markdown formatting around the JSON. Just the raw JSON array.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful JSON API that outputs only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        content = response.choices[0].message.content.strip()
        
        # Clean up any potential markdown formatting in case the model ignored instructions
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        tasks = json.loads(content.strip())
        
        # Validate format
        if isinstance(tasks, list) and all(isinstance(t, dict) and 'title' in t for t in tasks):
            return tasks
        else:
            logger.error("LLM returned invalid format for onboarding tasks")
            return default_tasks
            
    except Exception as e:
        logger.error(f"Error generating onboarding tasks with LLM: {e}")
        return default_tasks
