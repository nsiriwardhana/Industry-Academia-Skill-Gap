"""
Job Skill Extraction & Normalization Testing Endpoints

Separate endpoints to test and debug:
1. OCR extraction from JD images/PDFs
2. Raw skill extraction from text
3. Skill normalization (raw → canonical)
4. Complete pipeline testing

These endpoints help identify accuracy issues before running full gap analysis.
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional, Dict
from services.chandra_ocr_service import get_ocr_service
from services.skill_extract_service import get_skill_extract_service
from services.skill_normalize_llm import get_skill_normalize_service
from database.neo4j_connection import Neo4jConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/job-skill-test", tags=["Job Skill Testing"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TextExtractionRequest(BaseModel):
    """Request model for testing extraction from text."""
    jd_text: str


class ExtractionTestResponse(BaseModel):
    """Response for extraction testing."""
    success: bool
    job_title: str
    raw_required_skills: List[str]
    raw_optional_skills: List[str]
    extraction_metadata: Dict
    issues: List[str]
    recommendations: List[str]


class NormalizationTestResponse(BaseModel):
    """Response for normalization testing."""
    success: bool
    total_skills: int
    matched_count: int
    unmapped_count: int
    match_rate: float
    normalizations: List[Dict]
    issues: List[str]
    recommendations: List[str]


class CompleteTestResponse(BaseModel):
    """Response for complete pipeline test."""
    success: bool
    
    # Step 1: OCR
    ocr_extracted_text: str
    ocr_metadata: Dict
    
    # Step 2: Extraction
    job_title: str
    raw_required_skills: List[str]
    raw_optional_skills: List[str]
    extraction_metadata: Dict
    
    # Step 3: Normalization
    normalization_results: List[Dict]
    match_rate: float
    
    # Analysis
    issues: List[str]
    recommendations: List[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/extract-from-text", response_model=ExtractionTestResponse)
async def test_extraction_from_text(request: TextExtractionRequest):
    """
    Test raw skill extraction from plain text JD.
    
    Upload JD text directly to test extraction logic.
    No OCR, no normalization - just raw extraction.
    
    Returns:
    - Extracted skills (required & optional)
    - Extraction metadata
    - Issues and recommendations
    """
    logger.info("Testing skill extraction from text")
    
    try:
        # Get extractor service
        extractor = get_skill_extract_service()
        
        # Load KG skills if available
        try:
            with Neo4jConnection.get_session() as session:
                extractor.load_kg_skills(session)
        except Exception as e:
            logger.warning(f"Could not load KG skills: {e}")
        
        # Extract skills
        result = extractor.extract_skills(request.jd_text)
        
        # Analyze results
        issues = []
        recommendations = []
        
        req_count = len(result['raw_required_skills'])
        opt_count = len(result['raw_optional_skills'])
        
        if req_count == 0:
            issues.append("❌ CRITICAL: No required skills extracted")
            recommendations.append("Check if JD contains 'Required', 'Must Have', or 'Requirements' sections")
            recommendations.append("Verify JD text is properly formatted")
        elif req_count < 3:
            issues.append(f"⚠️ Only {req_count} required skills extracted (expected 5-15)")
            recommendations.append("JD may be poorly formatted or missing skills section")
        
        if result['extraction_metadata'].get('method') == 'keyword_fallback':
            issues.append("⚠️ Used fallback keyword matching (less accurate)")
            recommendations.append("JD structure doesn't match expected patterns - consider reformatting")
        
        return ExtractionTestResponse(
            success=True,
            job_title=result['job_title'],
            raw_required_skills=result['raw_required_skills'],
            raw_optional_skills=result['raw_optional_skills'],
            extraction_metadata=result['extraction_metadata'],
            issues=issues,
            recommendations=recommendations
        )
    
    except Exception as e:
        logger.error(f"Extraction test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction test failed: {str(e)}")


@router.post("/normalize-skills", response_model=NormalizationTestResponse)
async def test_skill_normalization(raw_skills: List[str]):
    """
    Test normalization of raw skill names to canonical forms.
    
    Upload a list of raw skill names to see how they map to KG skills.
    
    Returns:
    - Matched vs unmapped counts
    - Detailed normalization results
    - Issues and recommendations
    """
    logger.info(f"Testing normalization of {len(raw_skills)} skills")
    
    try:
        # Get normalizer service
        normalizer = get_skill_normalize_service()
        
        # Set Neo4j session
        try:
            with Neo4jConnection.get_session() as session:
                normalizer.set_session(session)
                
                # Normalize skills
                results = normalizer.normalize_skills_batch(raw_skills)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Neo4j connection failed: {str(e)}. Ensure Neo4j is running and has Skill nodes."
            )
        
        # Analyze results
        matched = [r for r in results if r['matched']]
        unmapped = [r for r in results if not r['matched']]
        match_rate = len(matched) / len(results) if results else 0
        
        issues = []
        recommendations = []
        
        if match_rate < 0.3:
            issues.append(f"❌ CRITICAL: Low match rate ({match_rate*100:.1f}%)")
            recommendations.append("Most skills not found in Knowledge Graph")
            recommendations.append("Run Graph-Builder to populate more skills")
        elif match_rate < 0.6:
            issues.append(f"⚠️ Medium match rate ({match_rate*100:.1f}%)")
            recommendations.append("Some skills using non-standard names")
        
        low_conf = [r for r in matched if r['confidence'] < 0.7]
        if low_conf:
            issues.append(f"⚠️ {len(low_conf)} low-confidence matches (<0.7)")
            recommendations.append("Review low-confidence matches - may be incorrect")
        
        if unmapped:
            recommendations.append(f"Add {len(unmapped)} unmapped skills to Knowledge Graph if valid")
        
        return NormalizationTestResponse(
            success=True,
            total_skills=len(results),
            matched_count=len(matched),
            unmapped_count=len(unmapped),
            match_rate=match_rate,
            normalizations=results,
            issues=issues,
            recommendations=recommendations
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Normalization test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Normalization test failed: {str(e)}")


@router.post("/complete-pipeline", response_model=CompleteTestResponse)
async def test_complete_pipeline(
    file: UploadFile = File(..., description="Job description image or PDF")
):
    """
    Test complete JD processing pipeline:
    1. OCR extraction (image/PDF → text)
    2. Skill extraction (text → raw skills)
    3. Skill normalization (raw → canonical)
    
    Upload a JD image/PDF to test the entire pipeline and identify issues.
    
    Returns:
    - OCR extracted text
    - Raw extracted skills
    - Normalized skills
    - Issues and recommendations at each step
    """
    logger.info(f"Testing complete pipeline with file: {file.filename}")
    
    try:
        # Read file content
        file_content = await file.read()
        content_type = file.content_type or "image/png"
        
        # Step 1: OCR Extraction
        logger.info("Step 1: OCR Extraction")
        ocr_service = get_ocr_service()
        
        try:
            extracted_text, ocr_metadata = await ocr_service.process_upload(
                file_content, content_type
            )
            
            if not extracted_text or len(extracted_text.strip()) < 50:
                return CompleteTestResponse(
                    success=False,
                    ocr_extracted_text=extracted_text,
                    ocr_metadata=ocr_metadata,
                    job_title="",
                    raw_required_skills=[],
                    raw_optional_skills=[],
                    extraction_metadata={},
                    normalization_results=[],
                    match_rate=0.0,
                    issues=["❌ CRITICAL: OCR extracted insufficient text (<50 chars)"],
                    recommendations=[
                        "Check image quality - may be blurry or low resolution",
                        "Ensure text is clearly visible in the image",
                        "Try uploading a different image format",
                        "Check EasyOCR fallback is working"
                    ]
                )
        
        except Exception as e:
            return CompleteTestResponse(
                success=False,
                ocr_extracted_text="",
                ocr_metadata={"error": str(e)},
                job_title="",
                raw_required_skills=[],
                raw_optional_skills=[],
                extraction_metadata={},
                normalization_results=[],
                match_rate=0.0,
                issues=[f"❌ CRITICAL: OCR failed - {str(e)}"],
                recommendations=[
                    "Check OCR service is running",
                    "Install EasyOCR: pip install easyocr",
                    "Verify image format is supported"
                ]
            )
        
        # Step 2: Skill Extraction
        logger.info("Step 2: Skill Extraction")
        extractor = get_skill_extract_service()
        
        try:
            with Neo4jConnection.get_session() as session:
                extractor.load_kg_skills(session)
        except Exception as e:
            logger.warning(f"Could not load KG skills: {e}")
        
        extraction_result = extractor.extract_skills(extracted_text)
        
        # Step 3: Normalization
        logger.info("Step 3: Normalization")
        normalizer = get_skill_normalize_service()
        normalization_results = []
        match_rate = 0.0
        
        all_raw_skills = (
            extraction_result['raw_required_skills'] + 
            extraction_result['raw_optional_skills']
        )
        
        if all_raw_skills:
            try:
                with Neo4jConnection.get_session() as session:
                    normalizer.set_session(session)
                    normalization_results = normalizer.normalize_skills_batch(all_raw_skills)
                    
                    matched_count = sum(1 for r in normalization_results if r['matched'])
                    match_rate = matched_count / len(normalization_results)
            except Exception as e:
                logger.error(f"Normalization failed: {e}")
        
        # Analyze overall results
        issues = []
        recommendations = []
        
        # OCR issues
        if len(extracted_text) < 200:
            issues.append("⚠️ OCR extracted short text (<200 chars)")
            recommendations.append("Check image quality and resolution")
        
        if ocr_metadata.get('source') == 'easyocr':
            issues.append("ℹ️ Used EasyOCR fallback (HuggingFace API unavailable)")
        
        # Extraction issues
        req_count = len(extraction_result['raw_required_skills'])
        if req_count == 0:
            issues.append("❌ CRITICAL: No required skills extracted")
            recommendations.append("OCR text may not contain skill sections")
            recommendations.append("Check if JD has 'Required Skills' or similar heading")
        elif req_count < 3:
            issues.append(f"⚠️ Only {req_count} required skills extracted")
            recommendations.append("JD may be poorly formatted")
        
        if extraction_result['extraction_metadata'].get('method') == 'keyword_fallback':
            issues.append("⚠️ Used keyword fallback for extraction")
            recommendations.append("JD structure doesn't match expected patterns")
        
        # Normalization issues
        if normalization_results:
            if match_rate < 0.3:
                issues.append(f"❌ Low normalization rate ({match_rate*100:.1f}%)")
                recommendations.append("Skills not in Knowledge Graph - add them or improve extraction")
            elif match_rate < 0.6:
                issues.append(f"⚠️ Medium normalization rate ({match_rate*100:.1f}%)")
        
        success = len(issues) == 0 or all("ℹ️" in issue or "⚠️" in issue for issue in issues)
        
        return CompleteTestResponse(
            success=success,
            ocr_extracted_text=extracted_text[:1000] + ("..." if len(extracted_text) > 1000 else ""),
            ocr_metadata=ocr_metadata,
            job_title=extraction_result['job_title'],
            raw_required_skills=extraction_result['raw_required_skills'],
            raw_optional_skills=extraction_result['raw_optional_skills'],
            extraction_metadata=extraction_result['extraction_metadata'],
            normalization_results=normalization_results,
            match_rate=match_rate,
            issues=issues,
            recommendations=recommendations
        )
    
    except Exception as e:
        logger.error(f"Complete pipeline test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline test failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Check if all services are available."""
    status = {
        "ocr_service": "unknown",
        "neo4j": "unknown",
        "ollama": "unknown"
    }
    
    # Check Neo4j
    try:
        with Neo4jConnection.get_session() as session:
            result = session.run("RETURN 1")
            result.single()
            status["neo4j"] = "✅ connected"
    except Exception as e:
        status["neo4j"] = f"❌ {str(e)}"
    
    # Check OCR service
    try:
        ocr_service = get_ocr_service()
        status["ocr_service"] = "✅ initialized"
    except Exception as e:
        status["ocr_service"] = f"❌ {str(e)}"
    
    # Check Ollama (optional)
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            status["ollama"] = "✅ running"
        else:
            status["ollama"] = "⚠️ not responding"
    except:
        status["ollama"] = "⚠️ not available (optional)"
    
    return status
