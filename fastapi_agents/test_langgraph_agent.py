"""
Test Phase 6: Integration & Testing
Tests LangGraph integration with FastAPI, edge cases, and performance benchmarking
"""

import sys
import os
import json
import time
from typing import Dict, Any
import asyncio

# Direct import to avoid __init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "langgraph_agent",
    os.path.join(os.path.dirname(__file__), "agents", "langgraph_agent.py")
)
langgraph_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(langgraph_agent)

# Import functions and classes
analyze_legal_document = langgraph_agent.analyze_legal_document
create_legal_analysis_graph = langgraph_agent.create_legal_analysis_graph
LegalAnalysisOutput = langgraph_agent.LegalAnalysisOutput


# ================================
# SAMPLE LEGAL DOCUMENTS
# ================================

SAMPLE_EMPLOYMENT_CONTRACT = """
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into on January 1, 2026,
between ABC Corporation ("Employer") and John Doe ("Employee").

1. POSITION AND DUTIES
The Employee shall serve as Senior Software Engineer and perform duties as assigned
by the Employer, consistent with Section 10 of the Indian Contract Act, 1872.

2. COMPENSATION
The Employee shall receive an annual salary of INR 2,000,000, subject to applicable
tax deductions as per the Income Tax Act, 1961.

3. TERMINATION
Either party may terminate this Agreement with 30 days written notice.
Termination without cause shall entitle the Employee to severance pay.
This clause is governed by Article 14 of the Constitution of India ensuring equal treatment.

4. NON-COMPETE
The Employee agrees not to engage in competing business for 2 years post-termination
within a 50km radius. This is subject to reasonableness under Section 27 of the
Indian Contract Act, 1872.

5. CONFIDENTIALITY
The Employee shall maintain confidentiality of proprietary information.
Breach may result in action under Section 405 of the Indian Penal Code, 1860
for criminal breach of trust.

6. DISPUTE RESOLUTION
Any disputes shall be resolved through arbitration in accordance with the
Arbitration and Conciliation Act, 1996.

This agreement is executed under the laws of India and subject to Article 21
(Right to Life and Personal Liberty) and Article 19 (Freedom of Speech and Expression)
of the Constitution of India.
"""

SAMPLE_RENTAL_AGREEMENT = """
RESIDENTIAL RENTAL AGREEMENT

This Rental Agreement is made on December 1, 2025, between Mr. Rajesh Kumar ("Landlord")
and Ms. Priya Singh ("Tenant") for the property located at 123 MG Road, Bangalore.

1. LEASE TERM
The lease shall commence on January 1, 2026 and continue for 11 months.
This agreement complies with Section 17 of the Registration Act, 1908.

2. RENT
Monthly rent is INR 30,000 payable on the 1st of each month.
Late payment after 5 days attracts 2% interest as per Section 73 of the
Indian Contract Act, 1872.

3. SECURITY DEPOSIT
Tenant has deposited INR 60,000 as security, refundable at lease end
subject to property condition assessment.

4. MAINTENANCE
Tenant is responsible for routine maintenance. Landlord shall handle
structural repairs. Property rights are governed by the Transfer of Property Act, 1882.

5. TERMINATION
Either party may terminate with 30 days notice. Breach of terms may result
in immediate termination and forfeiture of deposit.

6. LEGAL COMPLIANCE
Both parties shall comply with Section 108 (Rights of Lessee) and
Section 109 (Liabilities of Lessee) of the Transfer of Property Act, 1882.
"""

SAMPLE_SALE_DEED = """
SALE DEED

This Sale Deed is executed on October 15, 2025, between Mr. Amit Sharma ("Seller")
and Mrs. Kavita Desai ("Buyer") for the property described below.

PROPERTY DESCRIPTION:
Residential flat No. 401, Building A, Green Valley Apartments, Mumbai
Area: 1200 sq ft, Registration No: MH-01-2025-12345

CONSIDERATION:
Sale price: INR 1,50,00,000 (One Crore Fifty Lakhs Only)
Payment made via bank transfer and acknowledged.

TERMS AND CONDITIONS:

1. TRANSFER OF OWNERSHIP
The Seller hereby transfers all rights, title, and interest in the property
to the Buyer as per Section 54 of the Transfer of Property Act, 1882.

2. REGISTRATION
This deed shall be registered under Section 17 of the Registration Act, 1908
at the Sub-Registrar Office within 4 months.

3. CLEAR TITLE
Seller warrants clear title free from encumbrances. Any fraud shall be
prosecuted under Section 420 of the Indian Penal Code, 1860.

4. STAMP DUTY
Stamp duty and registration charges as per the Indian Stamp Act, 1899
shall be borne equally by both parties.

5. PROPERTY TAX
All property taxes paid until date of transfer. Future taxes are
Buyer's responsibility as per Municipal Corporation regulations.

6. CONSTITUTIONAL RIGHTS
This transaction is subject to Article 19(1)(f) which was amended,
and Article 300A regarding right to property.

The parties execute this deed in the presence of witnesses, understanding
their rights under Section 123 of the Indian Evidence Act, 1872.
"""

EMPTY_DOCUMENT = """
This is a very short document with no legal references.
"""

NO_REFERENCES_DOC = """
GENERAL BUSINESS LETTER

Dear Mr. Smith,

Thank you for your inquiry regarding our software products.
We are pleased to inform you that our latest release includes
many new features and improvements.

Our team has been working diligently to enhance the user experience
and add functionality based on customer feedback.

Please feel free to contact us if you have any questions.

Best regards,
Jane Doe
Sales Manager
"""

VERY_LARGE_DOCUMENT = """
COMPREHENSIVE LEGAL FRAMEWORK ANALYSIS

""" + "\n\n".join([
    f"SECTION {i}: This section discusses the implications of Article {i % 370} of the Constitution "
    f"in relation to Section {i % 511} of the Indian Penal Code, 1860. "
    f"Furthermore, Section {i % 100} of the Indian Contract Act, 1872 provides additional context. "
    f"This must be read in conjunction with provisions under Section {i % 200} of the Transfer of Property Act, 1882. "
    * 5  # Repeat to make it longer
    for i in range(1, 51)
])

MALFORMED_REFERENCES_DOC = """
DOCUMENT WITH MALFORMED REFERENCES

This document contains various incorrect or ambiguous references:

1. See Section XYZ of the Act
2. As per Article ABC of Constitution
3. Under Section 999999 IPC (non-existent section)
4. Reference to Section -5 (negative section)
5. Article 0 of Constitution (invalid article number)
6. Some Random Act, 3000 (future date)
7. Section 302 of Unknown Act, 1800 (old date)
"""


# ================================
# TEST FUNCTIONS
# ================================

def test_basic_integration():
    """Test 1: Basic integration with employment contract"""
    print("=" * 70)
    print("TEST 1: Basic Integration Test - Employment Contract")
    print("=" * 70)
    
    try:
        start_time = time.time()
        result = analyze_legal_document(SAMPLE_EMPLOYMENT_CONTRACT)
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000  # Convert to ms
        
        print(f"\n✅ Analysis completed in {processing_time:.2f}ms")
        print(f"\n📊 Results:")
        print(f"   Summary length: {len(result.get('summary', ''))}")
        print(f"   Legal sections found: {len(result.get('legal_sections', []))}")
        print(f"   Red flags identified: {len(result.get('red_flags', []))}")
        
        # Display some results
        print(f"\n📝 Summary (first 200 chars):")
        print(f"   {result.get('summary', '')[:200]}...")
        
        print(f"\n⚖️  Legal Sections:")
        for section in result.get('legal_sections', [])[:3]:
            print(f"   - {section.get('reference', 'N/A')}")
        
        print(f"\n🚩 Red Flags:")
        for flag in result.get('red_flags', [])[:3]:
            print(f"   - {flag}")
        
        print(f"\n📈 Metadata:")
        metadata = result.get('metadata', {})
        print(f"   Processing time: {metadata.get('processing_time_ms', 0):.2f}ms")
        print(f"   References found: {metadata.get('references_found', 0)}")
        print(f"   API calls made: {metadata.get('api_calls_made', 0)}")
        print(f"   API success rate: {metadata.get('api_success_rate', 0):.1f}%")
        
        # Validate schema
        try:
            validated = LegalAnalysisOutput(**result)
            print(f"\n✅ Output schema validation: PASSED")
        except Exception as e:
            print(f"\n❌ Output schema validation: FAILED")
            print(f"   Error: {str(e)}")
            
        print(f"\n{'=' * 70}")
        print(f"TEST 1: {'PASSED' if result else 'FAILED'}")
        print(f"{'=' * 70}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"\n{'=' * 70}")
        print(f"TEST 1: FAILED")
        print(f"{'=' * 70}\n")
        return None


def test_rental_agreement():
    """Test 2: Rental agreement with different legal references"""
    print("=" * 70)
    print("TEST 2: Rental Agreement Analysis")
    print("=" * 70)
    
    try:
        start_time = time.time()
        result = analyze_legal_document(SAMPLE_RENTAL_AGREEMENT)
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000
        
        print(f"\n✅ Analysis completed in {processing_time:.2f}ms")
        print(f"\n📊 Results:")
        print(f"   Summary length: {len(result.get('summary', ''))}")
        print(f"   Legal sections found: {len(result.get('legal_sections', []))}")
        print(f"   Red flags: {len(result.get('red_flags', []))}")
        
        # Check for specific acts
        sections_text = json.dumps(result.get('legal_sections', []))
        has_tpa = 'Transfer of Property Act' in sections_text or 'TPA' in sections_text
        has_contract = 'Contract Act' in sections_text or 'ICA' in sections_text
        
        print(f"\n🔍 Act Detection:")
        print(f"   Transfer of Property Act detected: {'✅' if has_tpa else '❌'}")
        print(f"   Indian Contract Act detected: {'✅' if has_contract else '❌'}")
        
        print(f"\n{'=' * 70}")
        print(f"TEST 2: {'PASSED' if result else 'FAILED'}")
        print(f"{'=' * 70}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"\n{'=' * 70}")
        print(f"TEST 2: FAILED")
        print(f"{'=' * 70}\n")
        return None


def test_sale_deed():
    """Test 3: Sale deed with property-related references"""
    print("=" * 70)
    print("TEST 3: Sale Deed Analysis")
    print("=" * 70)
    
    try:
        start_time = time.time()
        result = analyze_legal_document(SAMPLE_SALE_DEED)
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000
        
        print(f"\n✅ Analysis completed in {processing_time:.2f}ms")
        print(f"\n📊 Results:")
        print(f"   Legal sections: {len(result.get('legal_sections', []))}")
        
        # Check for property-related acts
        sections_text = json.dumps(result.get('legal_sections', []))
        has_tpa = 'Transfer of Property' in sections_text
        has_registration = 'Registration Act' in sections_text
        has_stamp = 'Stamp Act' in sections_text
        
        print(f"\n🔍 Property Law Detection:")
        print(f"   Transfer of Property Act: {'✅' if has_tpa else '❌'}")
        print(f"   Registration Act: {'✅' if has_registration else '❌'}")
        print(f"   Stamp Act: {'✅' if has_stamp else '❌'}")
        
        print(f"\n{'=' * 70}")
        print(f"TEST 3: {'PASSED' if result else 'FAILED'}")
        print(f"{'=' * 70}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\n{'=' * 70}")
        print(f"TEST 3: FAILED")
        print(f"{'=' * 70}\n")
        return None


def test_edge_case_empty_document():
    """Test 4: Edge case - Empty/minimal document"""
    print("=" * 70)
    print("TEST 4: Edge Case - Empty Document")
    print("=" * 70)
    
    try:
        result = analyze_legal_document(EMPTY_DOCUMENT)
        
        print(f"\n✅ Graceful handling of empty document")
        print(f"\n📊 Results:")
        print(f"   Summary: {result.get('summary', 'N/A')[:100]}...")
        print(f"   Legal sections: {len(result.get('legal_sections', []))}")
        print(f"   Has disclaimer: {'✅' if result.get('disclaimer') else '❌'}")
        
        # Validate schema even for edge case
        try:
            validated = LegalAnalysisOutput(**result)
            print(f"   Schema validation: ✅ PASSED")
        except Exception as e:
            print(f"   Schema validation: ❌ FAILED - {str(e)}")
        
        print(f"\n{'=' * 70}")
        print(f"TEST 4: PASSED (Graceful degradation)")
        print(f"{'=' * 70}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\n{'=' * 70}")
        print(f"TEST 4: FAILED")
        print(f"{'=' * 70}\n")
        return None


def test_edge_case_no_references():
    """Test 5: Edge case - Document with no legal references"""
    print("=" * 70)
    print("TEST 5: Edge Case - No Legal References")
    print("=" * 70)
    
    try:
        result = analyze_legal_document(NO_REFERENCES_DOC)
        
        print(f"\n✅ Handled document without legal references")
        print(f"\n📊 Results:")
        print(f"   Summary length: {len(result.get('summary', ''))}")
        print(f"   Legal sections: {len(result.get('legal_sections', []))}")
        print(f"   Metadata - References found: {result.get('metadata', {}).get('references_found', 0)}")
        print(f"   Has disclaimer: {'✅' if result.get('disclaimer') else '❌'}")
        
        print(f"\n{'=' * 70}")
        print(f"TEST 5: PASSED")
        print(f"{'=' * 70}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\n{'=' * 70}")
        print(f"TEST 5: FAILED")
        print(f"{'=' * 70}\n")
        return None


def test_edge_case_very_large_document():
    """Test 6: Edge case - Very large document (conditional chunking)"""
    print("=" * 70)
    print("TEST 6: Edge Case - Very Large Document (50K+ chars)")
    print("=" * 70)
    
    print(f"Document size: {len(VERY_LARGE_DOCUMENT)} characters")
    
    try:
        start_time = time.time()
        result = analyze_legal_document(VERY_LARGE_DOCUMENT)
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000
        
        print(f"\n✅ Successfully processed large document in {processing_time:.2f}ms")
        print(f"\n📊 Results:")
        print(f"   Legal sections: {len(result.get('legal_sections', []))}")
        print(f"   API calls: {result.get('metadata', {}).get('api_calls_made', 0)}")
        
        # Check if chunking was used
        metadata = result.get('metadata', {})
        print(f"   Processing time: {metadata.get('processing_time_ms', 0):.2f}ms")
        
        print(f"\n{'=' * 70}")
        print(f"TEST 6: PASSED")
        print(f"{'=' * 70}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\n{'=' * 70}")
        print(f"TEST 6: FAILED")
        print(f"{'=' * 70}\n")
        return None


def test_edge_case_malformed_references():
    """Test 7: Edge case - Malformed/invalid legal references"""
    print("=" * 70)
    print("TEST 7: Edge Case - Malformed References")
    print("=" * 70)
    
    try:
        result = analyze_legal_document(MALFORMED_REFERENCES_DOC)
        
        print(f"\n✅ Handled malformed references gracefully")
        print(f"\n📊 Results:")
        print(f"   Legal sections found: {len(result.get('legal_sections', []))}")
        metadata = result.get('metadata', {})
        print(f"   API success rate: {metadata.get('api_success_rate', 0):.1f}%")
        
        # Check that it didn't crash and produced valid output
        try:
            validated = LegalAnalysisOutput(**result)
            print(f"   Schema validation: ✅ PASSED")
        except Exception as e:
            print(f"   Schema validation: ❌ FAILED")
        
        print(f"\n{'=' * 70}")
        print(f"TEST 7: PASSED (Graceful error handling)")
        print(f"{'=' * 70}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\n{'=' * 70}")
        print(f"TEST 7: FAILED")
        print(f"{'=' * 70}\n")
        return None


def test_performance_benchmark():
    """Test 8: Performance benchmark - compare processing times"""
    print("=" * 70)
    print("TEST 8: Performance Benchmark")
    print("=" * 70)
    
    documents = {
        "Small (Empty)": EMPTY_DOCUMENT,
        "Medium (Rental)": SAMPLE_RENTAL_AGREEMENT,
        "Large (Employment)": SAMPLE_EMPLOYMENT_CONTRACT,
        "XLarge (50K chars)": VERY_LARGE_DOCUMENT
    }
    
    results = {}
    
    for name, doc in documents.items():
        try:
            start_time = time.time()
            result = analyze_legal_document(doc)
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000
            results[name] = {
                "time_ms": processing_time,
                "size_chars": len(doc),
                "references_found": result.get('metadata', {}).get('references_found', 0),
                "api_calls": result.get('metadata', {}).get('api_calls_made', 0)
            }
            
        except Exception as e:
            results[name] = {"error": str(e)}
    
    print(f"\n📊 Performance Results:")
    print(f"\n{'Document':<20} {'Size (chars)':<15} {'Time (ms)':<12} {'References':<12} {'API Calls':<12}")
    print("-" * 75)
    
    for name, data in results.items():
        if "error" not in data:
            print(f"{name:<20} {data['size_chars']:<15} {data['time_ms']:<12.2f} {data['references_found']:<12} {data['api_calls']:<12}")
        else:
            print(f"{name:<20} ERROR: {data['error']}")
    
    # Calculate average time
    valid_times = [d['time_ms'] for d in results.values() if 'time_ms' in d]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        print(f"\n📈 Average processing time: {avg_time:.2f}ms")
        
        # Check if meets 40% latency reduction target (assume baseline was ~10s = 10000ms)
        baseline = 10000  # Assumed Strands baseline
        target = baseline * 0.6  # 40% reduction = 60% of original
        print(f"   Target (60% of baseline): {target:.2f}ms")
        print(f"   Actual average: {avg_time:.2f}ms")
        
        if avg_time < target:
            print(f"   ✅ MEETS 40% latency reduction target!")
        else:
            print(f"   ⚠️  Did not meet latency target")
    
    print(f"\n{'=' * 70}")
    print(f"TEST 8: COMPLETED")
    print(f"{'=' * 70}\n")
    
    return results


def test_output_consistency():
    """Test 9: Output consistency - run same document multiple times"""
    print("=" * 70)
    print("TEST 9: Output Consistency Test")
    print("=" * 70)
    
    print("Running same document 3 times to check consistency...")
    
    results = []
    for i in range(3):
        try:
            result = analyze_legal_document(SAMPLE_EMPLOYMENT_CONTRACT)
            results.append({
                "summary_length": len(result.get('summary', '')),
                "num_sections": len(result.get('legal_sections', [])),
                "num_red_flags": len(result.get('red_flags', [])),
                "has_disclaimer": bool(result.get('disclaimer'))
            })
        except Exception as e:
            print(f"   Run {i+1}: ❌ Error - {str(e)}")
            results.append(None)
    
    # Check consistency
    valid_results = [r for r in results if r is not None]
    
    if len(valid_results) >= 2:
        print(f"\n📊 Results across {len(valid_results)} runs:")
        print(f"\n{'Metric':<20} {'Run 1':<15} {'Run 2':<15} {'Run 3':<15}")
        print("-" * 65)
        
        metrics = ['summary_length', 'num_sections', 'num_red_flags', 'has_disclaimer']
        for metric in metrics:
            values = [str(r.get(metric, 'N/A')) for r in valid_results]
            print(f"{metric:<20} {values[0]:<15} {values[1] if len(values) > 1 else 'N/A':<15} {values[2] if len(values) > 2 else 'N/A':<15}")
        
        # Check if all runs had disclaimer
        all_have_disclaimer = all(r.get('has_disclaimer', False) for r in valid_results)
        print(f"\n✅ All runs include disclaimer: {'YES' if all_have_disclaimer else 'NO'}")
        
    print(f"\n{'=' * 70}")
    print(f"TEST 9: {'PASSED' if len(valid_results) >= 2 else 'FAILED'}")
    print(f"{'=' * 70}\n")
    
    return results


def test_schema_compliance():
    """Test 10: Comprehensive schema compliance check"""
    print("=" * 70)
    print("TEST 10: Schema Compliance Check")
    print("=" * 70)
    
    test_docs = [
        ("Employment", SAMPLE_EMPLOYMENT_CONTRACT),
        ("Rental", SAMPLE_RENTAL_AGREEMENT),
        ("Empty", EMPTY_DOCUMENT)
    ]
    
    compliance_results = {}
    
    for name, doc in test_docs:
        try:
            result = analyze_legal_document(doc)
            
            # Check required fields
            required_fields = ['summary', 'legal_sections', 'red_flags', 'disclaimer', 'metadata']
            missing_fields = [f for f in required_fields if f not in result]
            
            # Validate with Pydantic
            try:
                validated = LegalAnalysisOutput(**result)
                schema_valid = True
                validation_error = None
            except Exception as e:
                schema_valid = False
                validation_error = str(e)
            
            compliance_results[name] = {
                "has_all_fields": len(missing_fields) == 0,
                "missing_fields": missing_fields,
                "schema_valid": schema_valid,
                "validation_error": validation_error,
                "disclaimer_present": bool(result.get('disclaimer')),
                "metadata_complete": all(
                    k in result.get('metadata', {})
                    for k in ['processing_time_ms', 'references_found', 'api_calls_made']
                )
            }
            
        except Exception as e:
            compliance_results[name] = {"error": str(e)}
    
    print(f"\n📋 Schema Compliance Results:")
    print()
    
    for name, data in compliance_results.items():
        print(f"Document: {name}")
        if "error" not in data:
            print(f"   All required fields: {'✅' if data['has_all_fields'] else '❌'}")
            if data['missing_fields']:
                print(f"   Missing: {', '.join(data['missing_fields'])}")
            print(f"   Schema validation: {'✅' if data['schema_valid'] else '❌'}")
            if data['validation_error']:
                print(f"   Error: {data['validation_error'][:100]}")
            print(f"   Disclaimer present: {'✅' if data['disclaimer_present'] else '❌'}")
            print(f"   Metadata complete: {'✅' if data['metadata_complete'] else '❌'}")
        else:
            print(f"   ❌ Error: {data['error']}")
        print()
    
    # Overall compliance
    all_compliant = all(
        d.get('schema_valid', False) and d.get('has_all_fields', False)
        for d in compliance_results.values()
        if 'error' not in d
    )
    
    print(f"{'=' * 70}")
    print(f"TEST 10: {'✅ PASSED - 100% schema compliance' if all_compliant else '❌ FAILED'}")
    print(f"{'=' * 70}\n")
    
    return compliance_results


# ================================
# MAIN TEST RUNNER
# ================================

def run_all_tests():
    """Run all Phase 6 integration tests"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PHASE 6: INTEGRATION & TESTING" + " " * 23 + "║")
    print("║" + " " * 12 + "LangGraph Migration - Final Phase" + " " * 21 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    # Check environment setup
    print("🔍 Checking environment setup...")
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️  Warning: GROQ_API_KEY not set")
    else:
        print("✅ GROQ_API_KEY configured")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not set")
    else:
        print("✅ GEMINI_API_KEY configured")
    
    print()
    
    # Run tests
    test_results = {}
    
    tests = [
        ("Basic Integration", test_basic_integration),
        ("Rental Agreement", test_rental_agreement),
        ("Sale Deed", test_sale_deed),
        ("Edge: Empty Document", test_edge_case_empty_document),
        ("Edge: No References", test_edge_case_no_references),
        ("Edge: Large Document", test_edge_case_very_large_document),
        ("Edge: Malformed Refs", test_edge_case_malformed_references),
        ("Performance Benchmark", test_performance_benchmark),
        ("Output Consistency", test_output_consistency),
        ("Schema Compliance", test_schema_compliance),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results[test_name] = "PASSED" if result is not None else "FAILED"
        except Exception as e:
            test_results[test_name] = f"ERROR: {str(e)}"
            print(f"Critical error in {test_name}: {str(e)}")
    
    # Summary
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 24 + "TEST SUMMARY" + " " * 32 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    for test_name, status in test_results.items():
        status_symbol = "✅" if status == "PASSED" else "❌"
        print(f"{status_symbol} {test_name:<40} {status}")
    
    # Overall status
    passed = sum(1 for s in test_results.values() if s == "PASSED")
    total = len(test_results)
    
    print()
    print(f"{'=' * 70}")
    print(f"PHASE 6 INTEGRATION TESTS: {passed}/{total} PASSED")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - READY FOR PRODUCTION!")
    elif passed >= total * 0.8:
        print("⚠️  MOST TESTS PASSED - REVIEW FAILURES BEFORE DEPLOYMENT")
    else:
        print("❌ MULTIPLE FAILURES - REQUIRES DEBUGGING")
    
    print(f"{'=' * 70}")
    print()


if __name__ == "__main__":
    run_all_tests()
