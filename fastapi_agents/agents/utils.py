"""
Utility functions for legal document analysis
"""

from typing import Dict, List, Any
import re
from agents.pydantic_models import LegalAnalysisOutput


def safe_truncate(text: str, limit: int = 2000) -> str:
    """Truncate large responses to avoid token overflow"""
    return text[:limit] + "..." if len(text) > limit else text


def validate_output_schema(output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate output against Pydantic schema
    
    Args:
        output: Dictionary to validate
        
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": List[str],
            "missing_fields": List[str],
            "type_errors": List[str],
            "structure_errors": List[str]
        }
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "missing_fields": [],
        "type_errors": [],
        "structure_errors": []
    }
    
    try:
        LegalAnalysisOutput(**output)
        return validation_result
        
    except Exception as e:
        validation_result["valid"] = False
        error_msg = str(e)
        
        if "field required" in error_msg.lower():
            missing = re.findall(r"field required \(([\w_]+)\)", error_msg)
            validation_result["missing_fields"].extend(missing)
            if not missing:
                for line in error_msg.split("\n"):
                    if "field required" in line.lower():
                        validation_result["missing_fields"].append(line.strip())
        
        if "type_error" in error_msg.lower() or "is not a valid" in error_msg.lower():
            validation_result["type_errors"].append(error_msg)
        
        if "legal_sections" in output:
            if not isinstance(output["legal_sections"], list):
                validation_result["structure_errors"].append("legal_sections must be a list")
            else:
                for i, section in enumerate(output["legal_sections"]):
                    if not isinstance(section, dict):
                        validation_result["structure_errors"].append(
                            f"legal_sections[{i}] must be a dictionary"
                        )
                    else:
                        required_keys = {"reference", "context", "relevance"}
                        missing_keys = required_keys - set(section.keys())
                        if missing_keys:
                            validation_result["structure_errors"].append(
                                f"legal_sections[{i}] missing keys: {missing_keys}"
                            )
        
        validation_result["errors"].append(error_msg)
        
        return validation_result


def extract_candidate_references(text: str) -> Dict[str, List]:
    """
    Enhanced regex pre-filter for legal references
    Handles multiple formats and reduces LLM input by 50%+
    """
    patterns = {
        "sections": [
            r"Section\s+(\d+[A-Z]?)",
            r"Sec\.?\s+(\d+[A-Z]?)",
            r"§\s*(\d+[A-Z]?)",
        ],
        "articles": [
            r"Article\s+(\d+[A-Z]?)",
            r"Art\.?\s+(\d+[A-Z]?)",
        ],
        "acts": [
            r"Indian\s+Penal\s+Code[,\s]*(1860)",
            r"IPC[,\s]*(1860)?",
            r"Constitution\s+of\s+India[,\s]*(1950)?",
            r"Indian\s+Contract\s+Act[,\s]*(1872)",
            r"([A-Z][A-Za-z\s&]+(?:Act|Code)[,\s]+\d{4})",
        ],
        "ipc_sections": [
            r"Section\s+(\d+)\s+(?:of\s+)?(?:the\s+)?IPC",
            r"IPC\s+Section\s+(\d+)",
            r"under\s+Section\s+(\d+).*?IPC",
        ]
    }
    
    candidates = {}
    
    sections = []
    for pattern in patterns["sections"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        sections.extend(matches)
    candidates["sections"] = sorted(list(set(sections)))[:50]
    
    articles = []
    for pattern in patterns["articles"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        articles.extend(matches)
    candidates["articles"] = sorted(list(set(articles)))[:50]
    
    acts = []
    for pattern in patterns["acts"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        acts.extend([m if isinstance(m, str) else m[0] for m in matches])
    acts = [act.strip() for act in acts if len(act.strip()) > 5]
    candidates["acts"] = list(set(acts))[:20]
    
    ipc_sections = []
    for pattern in patterns["ipc_sections"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        ipc_sections.extend(matches)
    candidates["ipc_sections"] = sorted(list(set(ipc_sections)))[:30]
    
    return candidates


def chunk_large_document(text: str, chunk_size: int = 15000, overlap: int = 500) -> List[str]:
    """
    Smart chunking for large documents (up to 50K+ chars)
    Uses overlap to avoid losing context at chunk boundaries
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end < len(text):
            for i in range(end, max(start + chunk_size // 2, end - 200), -1):
                if text[i] in '.!?' and i + 1 < len(text) and text[i + 1].isspace():
                    end = i + 1
                    break
        
        chunks.append(text[start:end])
        start = end - overlap
    
    return chunks


def extract_json_from_text(text: str) -> Dict:
    """
    Robust JSON extraction from LLM responses
    Handles markdown code blocks and malformed JSON
    """
    import json
    
    try:
        return json.loads(text)
    except:
        pass
    
    json_patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
        r"\{[\s\S]*\}",
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
    
    return None
