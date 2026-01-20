"""
Test Phase 5: Output Formatting Node Implementation
Tests JSON schema validation, default field filling, and metadata generation
"""

import sys
import os
import json
from typing import Dict, Any

# Direct import to avoid __init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "langgraph_agent",
    os.path.join(os.path.dirname(__file__), "agents", "langgraph_agent.py")
)
langgraph_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(langgraph_agent)

# Import functions and classes
LegalDocState = langgraph_agent.LegalDocState
validate_output_schema = langgraph_agent.validate_output_schema
formatting_node = langgraph_agent.formatting_node
create_legal_analysis_graph = langgraph_agent.create_legal_analysis_graph


def test_json_schema_validation():
    """Test 1: JSON schema validation with Pydantic"""
    print("=" * 60)
    print("TEST 1: JSON Schema Validation")
    print("=" * 60)
    
    # Valid output
    valid_output = {
        "summary": "This is a comprehensive legal analysis of the employment contract.",
        "legal_sections": [
            {
                "reference": "Article 21",
                "context": "Right to life and personal liberty",
                "relevance": "Protects employee rights"
            },
            {
                "reference": "Section 10, Indian Contract Act",
                "context": "What agreements are contracts",
                "relevance": "Validates contract formation"
            }
        ],
        "red_flags": [
            "Termination clause may be too broad",
            "Non-compete period exceeds reasonable limits"
        ],
        "disclaimer": "This is an AI-generated analysis for informational purposes only.",
        "metadata": {
            "processing_time_ms": 1234.56,
            "references_found": 5,
            "api_calls_made": 3,
            "api_success_rate": 66.7
        }
    }
    
    print("\n✅ Testing valid output:")
    result = validate_output_schema(valid_output)
    print(f"  Validation passed: {result['valid']}")
    print(f"  Errors: {result.get('errors', [])}")
    assert result['valid'] == True, f"Valid output should pass validation. Errors: {result.get('errors')}"
    
    # Invalid output - missing required fields
    invalid_output_missing = {
        "summary": "Short summary",
        # Missing legal_sections, red_flags, disclaimer, metadata
    }
    
    print("\n❌ Testing output with missing fields:")
    result = validate_output_schema(invalid_output_missing)
    print(f"  Validation passed: {result['valid']}")
    print(f"  Missing fields: {result.get('missing_fields', [])}")
    assert result['valid'] == False, "Output with missing fields should fail validation"
    assert len(result.get('missing_fields', [])) > 0, "Should identify missing fields"
    
    # Invalid output - wrong types
    invalid_output_types = {
        "summary": 123,  # Should be string
        "legal_sections": "not a list",  # Should be list
        "red_flags": {},  # Should be list
        "disclaimer": True,  # Should be string
        "metadata": []  # Should be dict
    }
    
    print("\n❌ Testing output with wrong types:")
    result = validate_output_schema(invalid_output_types)
    print(f"  Validation passed: {result['valid']}")
    print(f"  Type errors: {result.get('type_errors', [])}")
    assert result['valid'] == False, "Output with wrong types should fail validation"
    
    # Invalid output - malformed legal_sections
    invalid_output_sections = {
        "summary": "Summary text",
        "legal_sections": [
            {"reference": "Article 21"}  # Missing context and relevance
        ],
        "red_flags": [],
        "disclaimer": "Disclaimer text",
        "metadata": {}
    }
    
    print("\n❌ Testing output with malformed legal_sections:")
    result = validate_output_schema(invalid_output_sections)
    print(f"  Validation passed: {result['valid']}")
    print(f"  Structure errors: {result.get('structure_errors', [])}")
    assert result['valid'] == False, "Output with malformed sections should fail validation"
    
    print("\n✅ JSON schema validation test passed!")


def test_missing_field_defaults():
    """Test 2: Fill missing fields with appropriate defaults"""
    print("\n" + "=" * 60)
    print("TEST 2: Missing Field Defaults")
    print("=" * 60)
    
    # State with minimal final_output
    state: LegalDocState = {
        "raw_text": "Sample text",
        "references": {"sections": [{"act": "IPC", "section": "302"}], "articles": [21]},
        "fetched_data": {},
        "final_output": {
            "summary": "Brief summary"
            # Missing legal_sections, red_flags, disclaimer
        },
        "metadata": {
            "deduction_time_ms": 100,
            "fetch_time_ms": 200,
            "summarization_time_ms": 300,
            "api_calls_successful": 2,
            "api_calls_failed": 1
        }
    }
    
    print("\n🔧 Processing state with missing fields...")
    result_state = formatting_node(state)
    final_output = result_state["final_output"]
    
    print(f"\n✅ Checking default values:")
    print(f"  Summary present: {'✓' if final_output.get('summary') else '✗'}")
    print(f"  Summary: {final_output.get('summary')[:50]}...")
    assert final_output.get("summary"), "Summary should exist"
    
    print(f"  Legal sections present: {'✓' if 'legal_sections' in final_output else '✗'}")
    print(f"  Legal sections type: {type(final_output.get('legal_sections'))}")
    assert isinstance(final_output.get("legal_sections"), list), "Legal sections should be a list"
    
    print(f"  Red flags present: {'✓' if 'red_flags' in final_output else '✗'}")
    print(f"  Red flags type: {type(final_output.get('red_flags'))}")
    assert isinstance(final_output.get("red_flags"), list), "Red flags should be a list"
    
    print(f"  Disclaimer present: {'✓' if final_output.get('disclaimer') else '✗'}")
    print(f"  Disclaimer length: {len(final_output.get('disclaimer', ''))}")
    assert final_output.get("disclaimer"), "Disclaimer should exist"
    assert len(final_output["disclaimer"]) > 50, "Disclaimer should be comprehensive"
    
    print(f"  Metadata present: {'✓' if 'metadata' in final_output else '✗'}")
    assert "metadata" in final_output, "Metadata should exist"
    
    print("\n✅ Missing field defaults test passed!")


def test_metadata_generation():
    """Test 3: Generate comprehensive metadata"""
    print("\n" + "=" * 60)
    print("TEST 3: Metadata Generation")
    print("=" * 60)
    
    # State with complete data for metadata calculation
    state: LegalDocState = {
        "raw_text": "Sample legal document text",
        "references": {
            "sections": [
                {"act": "IPC", "section": "302"},
                {"act": "IPC", "section": "304"},
                {"act": "Indian Contract Act", "section": "10"}
            ],
            "articles": [21, 14],
            "acts": ["IPC, 1860", "Constitution, 1950"]
        },
        "fetched_data": {
            "sections": [
                {"reference": {"act": "IPC", "section": "302"}, "content": "..."}
            ],
            "articles": [
                {"article": "21", "content": "..."}
            ]
        },
        "final_output": {
            "summary": "Complete analysis of the legal document",
            "legal_sections": [
                {"reference": "Section 302 IPC", "context": "...", "relevance": "..."},
                {"reference": "Article 21", "context": "...", "relevance": "..."}
            ],
            "red_flags": ["Flag 1", "Flag 2"],
            "disclaimer": "Standard disclaimer"
        },
        "metadata": {
            "deduction_time_ms": 250.5,
            "fetch_time_ms": 450.75,
            "summarization_time_ms": 350.25,
            "api_calls_successful": 4,
            "api_calls_failed": 1,
            "deduction_chunks": 2,
            "fetch_parallel_batches": 2
        }
    }
    
    print("\n📊 Generating metadata...")
    result_state = formatting_node(state)
    metadata = result_state["final_output"]["metadata"]
    
    print(f"\n✅ Checking metadata fields:")
    print(f"  Processing time (ms): {metadata.get('processing_time_ms')}")
    assert "processing_time_ms" in metadata, "Should include processing time"
    expected_time = 250.5 + 450.75 + 350.25
    assert abs(metadata["processing_time_ms"] - expected_time) < 0.1, \
        f"Processing time should be {expected_time}, got {metadata['processing_time_ms']}"
    
    print(f"  References found: {metadata.get('references_found')}")
    assert "references_found" in metadata, "Should include references count"
    expected_refs = 3 + 2  # 3 sections + 2 articles
    assert metadata["references_found"] == expected_refs, \
        f"Should find {expected_refs} references, got {metadata['references_found']}"
    
    print(f"  API calls made: {metadata.get('api_calls_made')}")
    assert "api_calls_made" in metadata, "Should include API calls count"
    expected_calls = 4 + 1  # 4 successful + 1 failed
    assert metadata["api_calls_made"] == expected_calls, \
        f"Should have {expected_calls} API calls, got {metadata['api_calls_made']}"
    
    print(f"  API success rate: {metadata.get('api_success_rate'):.2f}%")
    assert "api_success_rate" in metadata, "Should include API success rate"
    expected_rate = (4 / 5) * 100  # 80%
    assert abs(metadata["api_success_rate"] - expected_rate) < 0.1, \
        f"Success rate should be {expected_rate}%, got {metadata['api_success_rate']}%"
    
    print("\n✅ Metadata generation test passed!")


def test_output_consistency():
    """Test 4: Ensure consistent output format across different inputs"""
    print("\n" + "=" * 60)
    print("TEST 4: Output Consistency")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "Empty state",
            "state": {
                "raw_text": "",
                "references": {},
                "fetched_data": {},
                "final_output": {},
                "metadata": {}
            }
        },
        {
            "name": "Minimal state",
            "state": {
                "raw_text": "Text",
                "references": {"sections": []},
                "fetched_data": {},
                "final_output": {"summary": "Summary"},
                "metadata": {"deduction_time_ms": 100}
            }
        },
        {
            "name": "Complete state",
            "state": {
                "raw_text": "Complete text",
                "references": {
                    "sections": [{"act": "IPC", "section": "302"}],
                    "articles": [21]
                },
                "fetched_data": {"sections": [{"content": "..."}]},
                "final_output": {
                    "summary": "Complete summary",
                    "legal_sections": [{"reference": "...", "context": "...", "relevance": "..."}],
                    "red_flags": ["Flag"],
                    "disclaimer": "Disclaimer"
                },
                "metadata": {
                    "deduction_time_ms": 100,
                    "fetch_time_ms": 200,
                    "summarization_time_ms": 300,
                    "api_calls_successful": 2,
                    "api_calls_failed": 0
                }
            }
        }
    ]
    
    required_fields = ["summary", "legal_sections", "red_flags", "disclaimer", "metadata"]
    metadata_fields = ["processing_time_ms", "references_found", "api_calls_made", "api_success_rate"]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing {test_case['name']}...")
        result_state = formatting_node(test_case["state"])
        final_output = result_state["final_output"]
        
        # Check all required fields exist
        for field in required_fields:
            assert field in final_output, \
                f"{test_case['name']}: Missing field '{field}'"
            print(f"  ✓ {field}")
        
        # Check metadata subfields
        print(f"  Metadata fields:")
        for field in metadata_fields:
            assert field in final_output["metadata"], \
                f"{test_case['name']}: Missing metadata field '{field}'"
            print(f"    ✓ {field}: {final_output['metadata'][field]}")
        
        # Check types
        assert isinstance(final_output["summary"], str), "Summary should be string"
        assert isinstance(final_output["legal_sections"], list), "Legal sections should be list"
        assert isinstance(final_output["red_flags"], list), "Red flags should be list"
        assert isinstance(final_output["disclaimer"], str), "Disclaimer should be string"
        assert isinstance(final_output["metadata"], dict), "Metadata should be dict"
    
    print("\n✅ Output consistency test passed!")


def test_edge_cases():
    """Test 5: Handle edge cases and error scenarios"""
    print("\n" + "=" * 60)
    print("TEST 5: Edge Cases and Error Handling")
    print("=" * 60)
    
    # Edge case 1: Very large numbers
    print("\n🔍 Testing large metric values...")
    state_large = {
        "raw_text": "Text",
        "references": {"sections": list(range(100)), "articles": list(range(50))},
        "fetched_data": {},
        "final_output": {"summary": "Summary"},
        "metadata": {
            "deduction_time_ms": 10000.0,
            "fetch_time_ms": 20000.0,
            "summarization_time_ms": 15000.0,
            "api_calls_successful": 100,
            "api_calls_failed": 10
        }
    }
    result = formatting_node(state_large)
    assert result["final_output"]["metadata"]["processing_time_ms"] == 45000.0
    assert result["final_output"]["metadata"]["references_found"] == 150
    assert result["final_output"]["metadata"]["api_calls_made"] == 110
    print(f"  ✓ Processing time: {result['final_output']['metadata']['processing_time_ms']}ms")
    print(f"  ✓ References: {result['final_output']['metadata']['references_found']}")
    print(f"  ✓ API calls: {result['final_output']['metadata']['api_calls_made']}")
    
    # Edge case 2: Zero values
    print("\n🔍 Testing zero values...")
    state_zero = {
        "raw_text": "",
        "references": {"sections": [], "articles": []},
        "fetched_data": {},
        "final_output": {},
        "metadata": {
            "deduction_time_ms": 0,
            "fetch_time_ms": 0,
            "summarization_time_ms": 0,
            "api_calls_successful": 0,
            "api_calls_failed": 0
        }
    }
    result = formatting_node(state_zero)
    assert result["final_output"]["metadata"]["processing_time_ms"] == 0
    assert result["final_output"]["metadata"]["references_found"] == 0
    assert result["final_output"]["metadata"]["api_calls_made"] == 0
    assert result["final_output"]["metadata"]["api_success_rate"] == 0.0
    print(f"  ✓ All metrics correctly handle zero values")
    
    # Edge case 3: None/missing values
    print("\n🔍 Testing missing/None values...")
    state_none = {
        "raw_text": "Text",
        "references": None,  # Should handle gracefully
        "fetched_data": {},
        "final_output": None,
        "metadata": None
    }
    result = formatting_node(state_none)
    assert "summary" in result["final_output"]
    assert "metadata" in result["final_output"]
    print(f"  ✓ Handles None values gracefully")
    
    # Edge case 4: All API calls failed
    print("\n🔍 Testing all failed API calls...")
    state_all_failed = {
        "raw_text": "Text",
        "references": {"sections": [{"act": "IPC", "section": "302"}]},
        "fetched_data": {},
        "final_output": {"summary": "Summary"},
        "metadata": {
            "deduction_time_ms": 100,
            "fetch_time_ms": 200,
            "summarization_time_ms": 150,
            "api_calls_successful": 0,
            "api_calls_failed": 5
        }
    }
    result = formatting_node(state_all_failed)
    assert result["final_output"]["metadata"]["api_success_rate"] == 0.0
    print(f"  ✓ Success rate correctly 0% when all calls fail")
    
    print("\n✅ Edge cases test passed!")


def test_end_to_end_formatting():
    """Test 6: End-to-end formatting workflow"""
    print("\n" + "=" * 60)
    print("TEST 6: End-to-End Formatting Workflow")
    print("=" * 60)
    
    # Simulate a complete state from previous nodes
    complete_state: LegalDocState = {
        "raw_text": """
        Employment Agreement dated January 1, 2026
        
        This agreement is governed by Article 21 of the Constitution of India, 1950
        and Section 10 of the Indian Contract Act, 1872. The employee agrees to
        a non-compete clause under Section 27 of the Indian Contract Act.
        
        Termination can occur under Article 14 provisions with one month notice.
        """,
        "references": {
            "sections": [
                {"act": "Indian Contract Act", "section": "10"},
                {"act": "Indian Contract Act", "section": "27"}
            ],
            "articles": [21, 14],
            "acts": ["Indian Contract Act, 1872", "Constitution of India, 1950"]
        },
        "fetched_data": {
            "sections": [
                {
                    "reference": {"act": "Indian Contract Act", "section": "10"},
                    "content": "Section 10 defines what agreements are contracts"
                },
                {
                    "reference": {"act": "Indian Contract Act", "section": "27"},
                    "content": "Section 27 states agreements in restraint of trade are void"
                }
            ],
            "articles": [
                {
                    "article": "21",
                    "content": "Article 21 protects life and personal liberty"
                },
                {
                    "article": "14",
                    "content": "Article 14 guarantees equality before law"
                }
            ]
        },
        "final_output": {
            "summary": "This employment agreement incorporates constitutional protections and contract law principles. "
                      "The agreement balances employer interests with employee rights, though certain clauses may need review.",
            "legal_sections": [
                {
                    "reference": "Article 21, Constitution of India",
                    "context": "Protection of life and personal liberty",
                    "relevance": "Ensures employee rights cannot be unduly restricted"
                },
                {
                    "reference": "Section 10, Indian Contract Act",
                    "context": "Defines valid contracts",
                    "relevance": "Establishes contractual validity"
                },
                {
                    "reference": "Section 27, Indian Contract Act",
                    "context": "Agreements in restraint of trade void",
                    "relevance": "Non-compete clause may be unenforceable"
                },
                {
                    "reference": "Article 14, Constitution of India",
                    "context": "Equality before law",
                    "relevance": "Ensures fair termination procedures"
                }
            ],
            "red_flags": [
                "Non-compete clause under Section 27 may be void",
                "Termination notice period should be reviewed for adequacy",
                "Ensure Article 21 protections not unduly restricted"
            ],
            "disclaimer": "This is an AI-generated legal analysis for informational purposes only."
        },
        "metadata": {
            "deduction_time_ms": 285.3,
            "fetch_time_ms": 523.7,
            "summarization_time_ms": 412.9,
            "api_calls_successful": 4,
            "api_calls_failed": 0,
            "deduction_chunks": 1,
            "fetch_parallel_batches": 2
        }
    }
    
    print("\n📋 Processing complete state through formatting node...")
    result_state = formatting_node(complete_state)
    final_output = result_state["final_output"]
    
    # Validate structure
    print("\n✅ Validating final output structure:")
    print(f"  Summary length: {len(final_output['summary'])} chars")
    assert len(final_output["summary"]) > 50, "Summary should be substantial"
    
    print(f"  Legal sections: {len(final_output['legal_sections'])} found")
    assert len(final_output["legal_sections"]) == 4, "Should have 4 legal sections"
    for section in final_output["legal_sections"]:
        assert "reference" in section, "Section should have reference"
        assert "context" in section, "Section should have context"
        assert "relevance" in section, "Section should have relevance"
    
    print(f"  Red flags: {len(final_output['red_flags'])} identified")
    assert len(final_output["red_flags"]) == 3, "Should have 3 red flags"
    
    print(f"  Disclaimer length: {len(final_output['disclaimer'])} chars")
    assert len(final_output["disclaimer"]) > 30, "Disclaimer should be present"
    
    # Validate metadata
    print(f"\n📊 Validating metadata:")
    metadata = final_output["metadata"]
    print(f"  Total processing time: {metadata['processing_time_ms']:.2f}ms")
    assert metadata["processing_time_ms"] == 285.3 + 523.7 + 412.9
    
    print(f"  References found: {metadata['references_found']}")
    assert metadata["references_found"] == 2 + 2  # 2 sections + 2 articles
    
    print(f"  API calls made: {metadata['api_calls_made']}")
    assert metadata["api_calls_made"] == 4
    
    print(f"  API success rate: {metadata['api_success_rate']:.2f}%")
    assert metadata["api_success_rate"] == 100.0
    
    # Validate schema
    print(f"\n🔍 Running schema validation...")
    validation_result = validate_output_schema(final_output)
    assert validation_result["valid"], f"Output should pass validation: {validation_result}"
    print(f"  Schema validation: ✓ PASSED")
    
    print("\n✅ End-to-end formatting test passed!")
    
    # Print sample output
    print("\n" + "=" * 60)
    print("SAMPLE FORMATTED OUTPUT:")
    print("=" * 60)
    print(json.dumps(final_output, indent=2))


def run_all_tests():
    """Run all Phase 5 tests"""
    print("\n" + "🚀" * 30)
    print("PHASE 5: OUTPUT FORMATTING - TEST SUITE")
    print("🚀" * 30 + "\n")
    
    tests = [
        ("JSON Schema Validation", test_json_schema_validation),
        ("Missing Field Defaults", test_missing_field_defaults),
        ("Metadata Generation", test_metadata_generation),
        ("Output Consistency", test_output_consistency),
        ("Edge Cases", test_edge_cases),
        ("End-to-End Formatting", test_end_to_end_formatting)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ {test_name} FAILED:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL PHASE 5 TESTS PASSED! 🎉")
        print("\nPhase 5 Acceptance Criteria Met:")
        print("  ✓ JSON schema validation passes")
        print("  ✓ Missing fields filled with defaults")
        print("  ✓ Metrics logged for monitoring")
        print("  ✓ Consistent output format")
        print("  ✓ Edge cases handled gracefully")
    else:
        print(f"\n⚠️  {failed} test(s) need attention")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
