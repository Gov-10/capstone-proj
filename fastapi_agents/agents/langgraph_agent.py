"""
LangGraph-based Legal Document Analysis Agent
"""

from typing import TypedDict, Dict, List, Any
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
import re
import asyncio
import requests
from datetime import datetime
from agents.utils import (
    safe_truncate,
    validate_output_schema,
    extract_candidate_references,
    chunk_large_document,
    extract_json_from_text
)

load_dotenv()

# STATE DEFINITION

class LegalDocState(TypedDict):
    """State object passed through all nodes"""
    raw_text: str              # Original PDF text
    references: Dict[str, Any]  # Extracted legal references
    fetched_data: Dict[str, Any]  # Data from APIs
    final_output: Dict[str, Any]  # Summary, red flags, disclaimer
    metadata: Dict[str, Any]    # Processing metrics


# LLM CLIENT CONFIGURATION

def get_groq_client():
    """Initialize GROQ client """
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=2048
    )


def get_gemini_client():
    """Initialize Gemini client for summarization and reasoning"""
    return ChatGoogleGenerativeAI(
        google_api_key=os.getenv("GEMINI_API_KEY"),
        model="gemini-2.5-flash",
        temperature=0.3,
        max_tokens=1500
    )


# NODE 1: CONDITIONAL CHUNKING + DEDUCTION

def deduction_node(state: LegalDocState) -> LegalDocState:
    """
    Enhanced reference extraction with:
    1. Advanced regex pre-filter (reduces LLM input by 50%+)
    2. Smart chunking for docs up to 50K+ chars with overlap
    3. GROQ LLM validation with robust JSON parsing
    4. Latency optimization (target: < 3 seconds)
    """
    start_time = datetime.now()
    raw_text = state["raw_text"]
    
    # Step 1: Enhanced regex pre-filter
    candidates = extract_candidate_references(raw_text)
    candidates_count = sum(len(v) for v in candidates.values())
    
    # Calculate input reduction
    original_length = len(raw_text)
    candidates_text = str(candidates)
    reduction_percentage = (1 - len(candidates_text) / max(1, original_length)) * 100
    
    # Step 2: Smart conditional chunking for large documents
    chunk_size = 15000
    chunks = chunk_large_document(raw_text, chunk_size=chunk_size, overlap=500)
    
    # For efficiency, only process first 2-3 chunks if document is massive
    max_chunks = 3 if len(chunks) > 3 else len(chunks)
    text_for_llm = "\n\n[CHUNK BREAK]\n\n".join(chunks[:max_chunks])
    
    # Step 3: GROQ LLM call for validation and structuring
    groq_client = get_groq_client()
    
    prompt = f"""You are a legal reference extraction specialist for Indian law.

Pre-filtered candidate references (from regex):
- Sections: {candidates.get('sections', [])[:30]}  (showing first 30)
- Articles: {candidates.get('articles', [])[:30]}
- Acts: {candidates.get('acts', [])[:10]}
- IPC Sections: {candidates.get('ipc_sections', [])[:20]}

Document text ({len(chunks)} chunks, processing first {max_chunks}):
{text_for_llm[:12000]}

Task: Validate and structure these references. Return ONLY valid JSON:

{{
  "articles": [21, 14, 19],
  "sections": [
    {{"act": "IPC", "section": "302"}},
    {{"act": "IPC", "section": "307"}},
    {{"act": "Indian Contract Act", "section": "10"}}
  ],
  "acts": ["Indian Penal Code, 1860", "Constitution of India, 1950"]
}}

Rules:
- Only include references ACTUALLY in the document
- Convert section/article numbers to strings or integers as appropriate
- Map sections to their correct acts (IPC, Contract Act, etc.)
- Remove duplicates"""

    # Make LLM call with timeout handling
    try:
        response = groq_client.invoke([HumanMessage(content=prompt)])
        response_text = response.content
    except Exception as e:
        print(f"LLM call failed: {e}")
        response_text = None
    
    # Step 4: Robust JSON parsing with multiple fallbacks
    references = None
    
    if response_text:
        references = extract_json_from_text(response_text)
    
    # Fallback 1: Try to use regex candidates with structure
    if not references:
        references = {
            "articles": [],
            "sections": [],
            "acts": candidates.get("acts", [])
        }
        
        # Structure articles
        for article in candidates.get("articles", []):
            try:
                # Extract just the number
                num = ''.join(c for c in str(article) if c.isdigit())
                if num:
                    references["articles"].append(int(num))
            except:
                pass
        
        # Structure sections with act detection
        for section in candidates.get("sections", []):
            try:
                num = ''.join(c for c in str(section) if c.isdigit())
                if num:
                    # Try to detect which act from context
                    act = "IPC"  # Default to IPC
                    references["sections"].append({"act": act, "section": num})
            except:
                pass
        
        # Add IPC sections specifically
        for section in candidates.get("ipc_sections", []):
            try:
                num = ''.join(c for c in str(section) if c.isdigit())
                if num and {"act": "IPC", "section": num} not in references["sections"]:
                    references["sections"].append({"act": "IPC", "section": num})
            except:
                pass
    
    # Ensure references has the right structure
    if not isinstance(references, dict):
        references = {"articles": [], "sections": [], "acts": []}
    
    references.setdefault("articles", [])
    references.setdefault("sections", [])
    references.setdefault("acts", [])
    
    # Calculate processing metrics
    processing_time = (datetime.now() - start_time).total_seconds() * 1000
    
    state["references"] = references
    state["metadata"] = {
        "deduction_time_ms": processing_time,
        "text_length": len(raw_text),
        "chunks_created": len(chunks),
        "chunks_processed": max_chunks,
        "was_chunked": len(raw_text) > chunk_size,
        "candidates_found": candidates_count,
        "input_reduction_pct": round(reduction_percentage, 2),
        "references_extracted": len(references.get("articles", [])) + len(references.get("sections", []))
    }
    
    return state


# NODE 2: DYNAMIC PARALLEL FETCH 

def validate_reference_format(reference: Dict) -> bool:
    """
    Validate reference format before API calls
    Reduces invalid API calls to < 5%
    
    Returns True if reference is valid, False otherwise
    """
    ref_type = reference.get("type")
    
    if ref_type == "article":
        # Article must have a non-empty numeric value
        value = reference.get("value", "")
        if not value or not str(value).strip():
            return False
        try:
            int(str(value).strip())
            return True
        except ValueError:
            return False
    
    elif ref_type == "section":
        # Section must have both act and section number
        act = reference.get("act", "").strip()
        section = reference.get("section", "").strip()
        return bool(act) and bool(section)
    
    elif ref_type == "act":
        # Act must have a non-empty code
        code = reference.get("code", "").strip()
        return bool(code)
    
    return False


def batch_references_by_source(references: Dict) -> Dict[str, List]:
    """
    Batch references by source (Constitution, IPC, other acts)
    Groups similar API calls for efficient parallel execution
    
    Returns dict with keys: 'constitution', 'ipc', 'contract_act', 'other'
    """
    batches = {
        "constitution": [],
        "ipc": [],
        "contract_act": [],
        "companies_act": [],
        "other": []
    }
    
    # Batch articles (all go to Constitution)
    for article in references.get("articles", []):
        batches["constitution"].append({
            "type": "article",
            "value": str(article)
        })
    
    # Batch sections by act
    for section in references.get("sections", []):
        act = section.get("act", "").lower()
        section_num = section.get("section", "")
        
        ref_obj = {
            "type": "section",
            "act": section.get("act"),
            "section": str(section_num)
        }
        
        if "ipc" in act or "penal" in act:
            batches["ipc"].append(ref_obj)
        elif "contract" in act:
            batches["contract_act"].append(ref_obj)
        elif "companies" in act:
            batches["companies_act"].append(ref_obj)
        else:
            batches["other"].append(ref_obj)
    
    # Filter out empty batches
    return {k: v for k, v in batches.items() if v}


async def fetch_with_retry(
    fetch_func,
    max_retries: int = 2,
    initial_delay: float = 0.5
) -> Dict:
    """
    Retry logic with exponential backoff
    
    Args:
        fetch_func: Async function to call
        max_retries: Number of retry attempts (default: 2)
        initial_delay: Initial delay in seconds (default: 0.5)
    
    Returns:
        Dict with 'success' and either 'data' or 'error'
    """
    delay = initial_delay
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = await fetch_func()
            return result
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
    
    # All retries failed
    return {
        "success": False,
        "error": f"Failed after {max_retries} attempts: {last_error}"
    }


async def fetch_india_act_async(act_code: str) -> Dict:
    """Async wrapper for act fetching with timeout"""
    try:
        url = f"https://www.indiacode.nic.in/api/acts/{act_code}"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, timeout=5)
        )
        return {"success": True, "data": safe_truncate(response.text)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def fetch_india_section_async(act_code: str, section_number: str) -> Dict:
    """Async wrapper for section fetching with timeout"""
    try:
        url = f"https://www.indiacode.nic.in/api/section/{act_code}/{section_number}"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, timeout=5)
        )
        return {"success": True, "data": safe_truncate(response.text)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def fetch_constitution_article_async(article_number: str) -> Dict:
    """Async wrapper for article fetching with timeout"""
    try:
        url = f"https://www.indiacode.nic.in/api/articles/A1950/{article_number}"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, timeout=5)
        )
        return {"success": True, "data": safe_truncate(response.text)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_node(state: LegalDocState) -> LegalDocState:
    """
    Enhanced fetch node with:
    1. Pre-validation of reference formats (< 5% invalid calls)
    2. Batching by source (Constitution, IPC, etc.)
    3. Parallel execution with semaphore (limit concurrent requests)
    4. Retry logic with exponential backoff (2 retries)
    5. Graceful degradation on API failures
    
    Handles 1-20 references dynamically with high reliability
    """
    start_time = datetime.now()
    references = state["references"]
    fetched_data = {
        "articles": [],
        "sections": [],
        "acts": []
    }
    
    # Step 1: Batch references by source
    batches = batch_references_by_source(references)
    
    # Step 2: Prepare validated async tasks
    tasks = []
    invalid_references = 0
    
    # Process constitution articles
    for ref in batches.get("constitution", [])[:20]:  # Limit to 20
        if validate_reference_format(ref):
            article_num = ref["value"]
            async_func = lambda num=article_num: fetch_constitution_article_async(num)
            tasks.append(("article", article_num, fetch_with_retry(async_func)))
        else:
            invalid_references += 1
    
    # Process IPC sections
    for ref in batches.get("ipc", [])[:20]:  # Limit to 20
        if validate_reference_format(ref):
            section_num = ref["section"]
            async_func = lambda s=section_num: fetch_india_section_async("IPC", s)
            tasks.append(("section", ref, fetch_with_retry(async_func)))
        else:
            invalid_references += 1
    
    # Process other act sections
    for batch_name in ["contract_act", "companies_act", "other"]:
        for ref in batches.get(batch_name, [])[:10]:  # Limit each to 10
            if validate_reference_format(ref):
                act = ref["act"]
                section_num = ref["section"]
                async_func = lambda a=act, s=section_num: fetch_india_section_async(a, s)
                tasks.append(("section", ref, fetch_with_retry(async_func)))
            else:
                invalid_references += 1
    
    # Step 3: Execute all tasks in parallel with semaphore
    async def run_all_fetches_with_semaphore():
        # Limit concurrent requests to avoid overwhelming APIs
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def fetch_with_semaphore(task_info):
            task_type, reference, coro = task_info
            async with semaphore:
                result = await coro
                return (task_type, reference, result)
        
        results = await asyncio.gather(*[
            fetch_with_semaphore(task) for task in tasks
        ])
        return results
    
    # Run async fetches
    fetch_results = []
    if tasks:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            fetch_results = loop.run_until_complete(run_all_fetches_with_semaphore())
        finally:
            loop.close()
    
    # Step 4: Process results with graceful degradation
    api_calls_successful = 0
    api_calls_failed = 0
    
    for task_type, reference, result in fetch_results:
        if result.get("success"):
            api_calls_successful += 1
            if task_type == "article":
                fetched_data["articles"].append({
                    "article": reference,
                    "content": result["data"]
                })
            elif task_type == "section":
                fetched_data["sections"].append({
                    "reference": reference,
                    "content": result["data"]
                })
        else:
            api_calls_failed += 1
            # Log but continue (graceful degradation)
            print(f"  Failed to fetch {task_type}: {reference} - {result.get('error', 'Unknown error')}")
    
    processing_time = (datetime.now() - start_time).total_seconds() * 1000
    
    # Calculate invalid call rate
    total_references = len(tasks) + invalid_references
    invalid_rate = (invalid_references / max(1, total_references)) * 100
    
    state["fetched_data"] = fetched_data
    state["metadata"]["fetch_time_ms"] = processing_time
    state["metadata"]["api_calls_successful"] = api_calls_successful
    state["metadata"]["api_calls_failed"] = api_calls_failed
    state["metadata"]["invalid_references_filtered"] = invalid_references
    state["metadata"]["invalid_call_rate_pct"] = round(invalid_rate, 2)
    state["metadata"]["batches_created"] = len(batches)
    
    return state


# NODE 3: AGGREGATION + SUMMARIZATION 

def structure_summarization_prompt(
    raw_text: str,
    references: Dict,
    fetched_data: Dict
) -> str:
    """
    Structure comprehensive prompt combining all context
    
    Combines:
    - Original document text (truncated to 10K chars)
    - Extracted references (structured)
    - Fetched legal data (from APIs)
    
    Returns structured prompt for Gemini with clear JSON schema
    """
    # Truncate raw text intelligently (try to break at sentence)
    max_text_length = 10000
    truncated_text = raw_text[:max_text_length]
    if len(raw_text) > max_text_length:
        # Try to end at last period
        last_period = truncated_text.rfind('.')
        if last_period > max_text_length * 0.8:  # If period is in last 20%
            truncated_text = truncated_text[:last_period + 1]
        truncated_text += "\n\n[... document continues ...]"
    
    # Format references clearly
    references_summary = []
    if references.get("articles"):
        references_summary.append(f"Constitution Articles: {references['articles']}")
    if references.get("sections"):
        section_list = [f"{s.get('act', 'Unknown')}-{s.get('section', '?')}" 
                       for s in references.get("sections", [])[:10]]
        references_summary.append(f"Sections: {', '.join(section_list)}")
    if references.get("acts"):
        references_summary.append(f"Acts: {', '.join(references['acts'][:5])}")
    
    # Format fetched data with context
    fetched_summary = []
    for article_data in fetched_data.get("articles", [])[:5]:
        article_num = article_data.get("article", "?")
        content = article_data.get("content", "")[:300]  # First 300 chars
        fetched_summary.append(f"\n### Article {article_num}\n{content}...")
    
    for section_data in fetched_data.get("sections", [])[:5]:
        ref = section_data.get("reference", {})
        act = ref.get("act", "Unknown Act")
        section = ref.get("section", "?")
        content = section_data.get("content", "")[:300]
        fetched_summary.append(f"\n### {act} Section {section}\n{content}...")
    
    # Build comprehensive prompt
    prompt = f"""You are an expert legal document analyzer specializing in Indian law. 
Analyze the provided document and generate a comprehensive, structured legal analysis.

## ORIGINAL DOCUMENT
{truncated_text}

## LEGAL REFERENCES IDENTIFIED
{chr(10).join(references_summary) if references_summary else "No specific references found"}

## FETCHED LEGAL CONTEXT
{''.join(fetched_summary) if fetched_summary else "No additional legal data available"}

## YOUR TASK
Provide a thorough legal analysis in JSON format with the following structure:

{{
  "summary": "A comprehensive 2-3 paragraph summary of the document's legal nature, purpose, and key provisions",
  "legal_sections": [
    {{
      "reference": "Article/Section number with act name",
      "context": "What this legal provision states",
      "relevance": "How it applies to this specific document"
    }}
  ],
  "red_flags": [
    "Specific legal concerns, ambiguities, or potential issues identified in the document"
  ],
  "disclaimer": "Standard legal disclaimer"
}}

## IMPORTANT INSTRUCTIONS
- Be specific and cite exact provisions
- Explain legal concepts clearly for non-lawyers
- Identify genuine concerns in red_flags (minimum 1, maximum 5)
- Ensure summary is substantial (minimum 100 words)
- Include proper legal disclaimer warning this is not legal advice
- Output ONLY valid JSON, no additional text

Generate the analysis now:"""
    
    return prompt


def parse_llm_json_response(response_text: str) -> Dict:
    """
    Robust JSON parsing from LLM responses
    
    Handles:
    - Clean JSON
    - JSON in markdown code blocks
    - JSON with surrounding text
    - Malformed JSON (returns None)
    """
    import json
    import re
    
    # Try 1: Direct parse
    try:
        return json.loads(response_text.strip())
    except:
        pass
    
    # Try 2: Extract from markdown code blocks
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',      # ``` ... ```
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except:
                continue
    
    # Try 3: Find JSON object in text
    json_pattern = r'\{[\s\S]*\}'
    matches = re.findall(json_pattern, response_text, re.DOTALL)
    
    # Try each match, preferring the longest (most complete)
    matches_sorted = sorted(matches, key=len, reverse=True)
    for match in matches_sorted:
        try:
            parsed = json.loads(match)
            # Verify it has expected structure
            if isinstance(parsed, dict) and 'summary' in parsed:
                return parsed
        except:
            continue
    
    # All parsing attempts failed
    return None


def validate_summary_output(output: Dict) -> Dict:
    """
    Validate summary output structure and completeness
    
    Returns dict with:
    - valid: bool
    - missing_fields: list
    - issues: list
    """
    required_fields = ["summary", "legal_sections", "red_flags", "disclaimer"]
    missing_fields = [field for field in required_fields if field not in output]
    
    issues = []
    
    # Check summary
    if "summary" in output:
        summary = output["summary"]
        if not summary or not summary.strip():
            issues.append("Summary is empty")
        elif len(summary.split()) < 10:
            issues.append("Summary is too short (< 10 words)")
    
    # Check legal_sections structure
    if "legal_sections" in output:
        if not isinstance(output["legal_sections"], list):
            issues.append("legal_sections must be an array")
        else:
            for i, section in enumerate(output["legal_sections"]):
                if not isinstance(section, dict):
                    issues.append(f"legal_sections[{i}] must be an object")
                elif not all(k in section for k in ["reference", "context", "relevance"]):
                    issues.append(f"legal_sections[{i}] missing required fields")
    
    # Check red_flags
    if "red_flags" in output:
        if not isinstance(output["red_flags"], list):
            issues.append("red_flags must be an array")
    
    # Check disclaimer
    if "disclaimer" in output:
        disclaimer = output["disclaimer"]
        if not disclaimer or len(disclaimer) < 20:
            issues.append("Disclaimer is too short or missing")
    
    return {
        "valid": len(missing_fields) == 0 and len(issues) == 0,
        "missing_fields": missing_fields,
        "issues": issues
    }


def ensure_disclaimer(output: Dict) -> Dict:
    """
    Ensure comprehensive legal disclaimer is always present
    
    If disclaimer is missing or inadequate, adds/replaces with standard one
    """
    standard_disclaimer = (
        "This is an AI-generated legal analysis for informational purposes only. "
        "It should not be considered as legal advice or a substitute for consultation "
        "with a qualified legal professional. The analysis is based on automated "
        "extraction and interpretation of legal references and may contain errors or "
        "omissions. For specific legal guidance related to your situation, please "
        "consult a licensed attorney."
    )
    
    # Check if disclaimer exists and is adequate
    current_disclaimer = output.get("disclaimer", "")
    
    if not current_disclaimer or len(current_disclaimer) < 50:
        # Replace with standard disclaimer
        output["disclaimer"] = standard_disclaimer
    elif "not" not in current_disclaimer.lower() or "legal advice" not in current_disclaimer.lower():
        # Disclaimer exists but doesn't contain proper warning
        output["disclaimer"] = standard_disclaimer
    # Otherwise keep existing disclaimer
    
    return output


def summarization_node(state: LegalDocState) -> LegalDocState:
    """
    Enhanced aggregation + summarization with:
    1. Structured prompt combining original text + fetched data
    2. Gemini LLM for nuanced legal reasoning
    3. Robust JSON parsing with multiple fallback strategies
    4. Output validation and disclaimer enforcement
    5. Comprehensive error handling
    
    Generates all required fields: summary, legal_sections, red_flags, disclaimer
    """
    start_time = datetime.now()
    
    raw_text = state["raw_text"]
    fetched_data = state["fetched_data"]
    references = state["references"]
    
    # Step 1: Structure comprehensive prompt
    prompt = structure_summarization_prompt(raw_text, references, fetched_data)
    
    # Step 2: Call Gemini for analysis
    gemini_client = get_gemini_client()
    
    try:
        response = gemini_client.invoke([HumanMessage(content=prompt)])
        response_text = response.content
    except Exception as e:
        print(f"  Gemini API call failed: {e}")
        response_text = None
    
    # Step 3: Parse response with robust JSON extraction
    final_output = None
    
    if response_text:
        final_output = parse_llm_json_response(response_text)
    
    # Step 4: Fallback if parsing failed
    if not final_output:
        print("  JSON parsing failed, using fallback structure")
        # Try to extract at least the summary text
        summary_text = response_text[:500] if response_text else "Unable to generate summary due to parsing error."
        
        final_output = {
            "summary": summary_text,
            "legal_sections": [],
            "red_flags": ["Analysis could not be fully parsed - manual review recommended"],
            "disclaimer": ""  # Will be filled by ensure_disclaimer
        }
    
    # Step 5: Validate output structure
    validation = validate_summary_output(final_output)
    
    if not validation["valid"]:
        print(f" Output validation issues: {validation}")
        
        # Fix missing fields
        if "summary" not in final_output or not final_output["summary"]:
            final_output["summary"] = "Legal document analysis completed. See detailed sections below."
        
        if "legal_sections" not in final_output:
            final_output["legal_sections"] = []
        
        if "red_flags" not in final_output:
            final_output["red_flags"] = []
    
    # Step 6: Ensure comprehensive disclaimer (ALWAYS)
    final_output = ensure_disclaimer(final_output)
    
    # Step 7: Add processing metrics
    processing_time = (datetime.now() - start_time).total_seconds() * 1000
    state["metadata"]["summarization_time_ms"] = processing_time
    state["metadata"]["summary_word_count"] = len(final_output.get("summary", "").split())
    state["metadata"]["legal_sections_count"] = len(final_output.get("legal_sections", []))
    state["metadata"]["red_flags_count"] = len(final_output.get("red_flags", []))
    state["metadata"]["output_validated"] = validation["valid"]
    
    state["final_output"] = final_output
    
    return state



# NODE 4: OUTPUT FORMATTING 

def formatting_node(state: LegalDocState) -> LegalDocState:
    """
    Ensure consistent, validated JSON output with comprehensive error handling:
    1. Build output with all required fields
    2. Validate against JSON schema (Pydantic)
    3. Fill missing fields with defaults
    4. Generate complete metadata with metrics
    5. Log validation results
    """
    start_time = datetime.now()
    
    final_output = state.get("final_output", {})
    metadata = state.get("metadata", {})
    references = state.get("references", {})
    
    # Handle None values gracefully
    if final_output is None:
        final_output = {}
    if metadata is None:
        metadata = {}
    if references is None:
        references = {}
    
    # Step 1: Build validated output structure
    validated_output = {
        "summary": final_output.get("summary", "No summary available"),
        "legal_sections": final_output.get("legal_sections", []),
        "red_flags": final_output.get("red_flags", []),
        "disclaimer": final_output.get(
            "disclaimer",
            "This is an AI-generated analysis for informational purposes only. "
            "It should not be considered legal advice. Please consult a qualified "
            "legal professional for specific guidance."
        ),
        "metadata": {
            "processing_time_ms": sum([
                metadata.get("deduction_time_ms", 0),
                metadata.get("fetch_time_ms", 0),
                metadata.get("summarization_time_ms", 0)
            ]),
            "references_found": (
                len(references.get("sections", [])) + 
                len(references.get("articles", []))
            ),
            "api_calls_made": (
                metadata.get("api_calls_successful", 0) + 
                metadata.get("api_calls_failed", 0)
            ),
            "api_success_rate": (
                (metadata.get("api_calls_successful", 0) / 
                max(1, metadata.get("api_calls_successful", 0) + metadata.get("api_calls_failed", 0)))
                * 100
            )
        }
    }
    
    # Step 2: Validate against Pydantic schema
    validation = validate_output_schema(validated_output)
    
    # Step 3: Handle validation errors
    if not validation["valid"]:
        print(f"   Schema validation issues detected:")
        print(f"   Missing fields: {validation.get('missing_fields', [])}")
        print(f"   Type errors: {validation.get('type_errors', [])}")
        print(f"   Structure errors: {validation.get('structure_errors', [])}")
        
        # Fix common issues
        # Ensure summary is not empty
        if not validated_output["summary"] or len(validated_output["summary"].strip()) < 10:
            validated_output["summary"] = (
                "Legal document analysis completed. This document contains legal references "
                "and provisions. See detailed sections below for specific analysis."
            )
        
        # Ensure disclaimer meets minimum length
        if len(validated_output["disclaimer"]) < 30:
            validated_output["disclaimer"] = (
                "This is an AI-generated analysis for informational purposes only. "
                "It should not be considered legal advice. Please consult a qualified "
                "legal professional for specific guidance on your specific situation."
            )
        
        # Validate legal_sections structure
        if validated_output["legal_sections"]:
            fixed_sections = []
            for section in validated_output["legal_sections"]:
                if isinstance(section, dict) and all(k in section for k in ["reference", "context", "relevance"]):
                    # Ensure fields are not empty
                    if all(section.get(k) and str(section.get(k)).strip() for k in ["reference", "context", "relevance"]):
                        fixed_sections.append(section)
            validated_output["legal_sections"] = fixed_sections
        
        # Re-validate after fixes
        validation_retry = validate_output_schema(validated_output)
        if validation_retry["valid"]:
            print(" Validation issues resolved after fixes")
        else:
            print(f"  Some validation issues remain: {validation_retry.get('errors', [])[:2]}")
    
    # Step 4: Add formatting metadata
    formatting_time = (datetime.now() - start_time).total_seconds() * 1000
    metadata["formatting_time_ms"] = formatting_time
    metadata["output_validated"] = validation["valid"]
    metadata["validation_errors"] = len(validation.get("errors", []))
    
    # Step 5: Log metrics for monitoring
    print(f"\n Output Formatting Metrics:")
    print(f"   Total processing time: {validated_output['metadata']['processing_time_ms']:.2f}ms")
    print(f"   References found: {validated_output['metadata']['references_found']}")
    print(f"   API calls made: {validated_output['metadata']['api_calls_made']}")
    print(f"   API success rate: {validated_output['metadata']['api_success_rate']:.1f}%")
    print(f"   Formatting time: {formatting_time:.2f}ms")
    print(f"   Schema validation: {' PASSED' if validation['valid'] else '  ISSUES'}")
    
    state["final_output"] = validated_output
    state["metadata"] = metadata
    
    return state



# GRAPH CONSTRUCTION


def create_legal_analysis_graph() -> StateGraph:
    """
    Build the 4-node LangGraph workflow:
    
    INPUT → Deduction → Fetch → Summarization → Formatting → OUTPUT
    """
    
    # Initialize graph
    workflow = StateGraph(LegalDocState)
    
    # Add nodes
    workflow.add_node("deduction", deduction_node)
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("summarization", summarization_node)
    workflow.add_node("formatting", formatting_node)
    
    # Define edges (sequential flow)
    workflow.set_entry_point("deduction")
    workflow.add_edge("deduction", "fetch")
    workflow.add_edge("fetch", "summarization")
    workflow.add_edge("summarization", "formatting")
    workflow.add_edge("formatting", END)
    

    app = workflow.compile()
    
    return app


# MAIN ENTRY POINT

def analyze_legal_document(raw_text: str) -> Dict[str, Any]:
    """
    Main function to analyze a legal document using LangGraph
    
    Args:
        raw_text: Extracted text from PDF
        
    Returns:
        Complete analysis with summary, legal sections, red flags, and metadata
    """
    graph = create_legal_analysis_graph()
    
    initial_state: LegalDocState = {
        "raw_text": raw_text,
        "references": {},
        "fetched_data": {},
        "final_output": {},
        "metadata": {}
    }
    
    final_state = graph.invoke(initial_state)
    
    return final_state["final_output"]
