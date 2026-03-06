"""
Ollama client for LLM-based quiz generation using lightweight JSON format.
"""

import json
import logging
import requests
from typing import Dict, List, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"
MAX_RETRIES = 3


def parse_json_loose(text: str) -> dict:
    """
    Parse JSON from text with fallback strategies.
    
    Args:
        text: Text that should contain JSON
        
    Returns:
        Parsed JSON dict
        
    Raises:
        ValueError: If JSON cannot be parsed
    """
    text = text.strip()
    
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Remove markdown code fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    # Try again after fence removal
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Extract from first { to last }
    try:
        first_brace = text.index("{")
        last_brace = text.rindex("}")
        json_substr = text[first_brace:last_brace + 1]
        return json.loads(json_substr)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse JSON. First 200 chars: {text[:200]}")


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, num_predict: int = 200) -> dict:
    """
    Call Ollama Generate API with lightweight JSON format.
    
    Args:
        prompt: The prompt to send to Ollama
        model: Model name (default: llama3.1:8b)
        num_predict: Maximum tokens to predict
        
    Returns:
        Full Ollama JSON response
        
    Raises:
        HTTPException: If Ollama is not reachable
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",  # Lightweight JSON enforcement
        "options": {
            "temperature": 0.3,  # Slightly higher for faster sampling
            "top_p": 0.85,  # Reduced for faster token selection
            "num_predict": num_predict,
            "num_ctx": 2048  # Reduce context window for speed
        }
    }
    
    try:
        logger.debug(f"Calling Ollama /api/generate with format=json, num_predict={num_predict}")
        response = requests.post(url, json=payload, timeout=240)  # 4 minutes timeout
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Ollama not reachable at {OLLAMA_BASE_URL}/api/generate")
        raise HTTPException(
            status_code=503,
            detail=f"Ollama not reachable at {OLLAMA_BASE_URL} (endpoint: /api/generate)"
        )
    except requests.exceptions.Timeout:
        logger.error(f"Ollama /api/generate request timeout (240s, num_predict={num_predict})")
        # Retry with reduced tokens
        if num_predict > 180:
            logger.info("Retrying with reduced num_predict=180")
            return call_ollama(prompt, model, num_predict=180)
        raise HTTPException(
            status_code=504,
            detail="Ollama /api/generate request timeout even with reduced tokens."
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama /api/generate request failed: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Ollama /api/generate request failed: {str(e)}"
        )


def generate_mcq(
    skill_name: str,
    difficulty: str,
    scope_bullets: List[str],
    model: str = DEFAULT_MODEL
) -> dict:
    """
    Generate a multiple-choice question using Ollama with lightweight JSON format.
    
    Args:
        skill_name: Parent skill name
        difficulty: Question difficulty (easy, medium, hard)
        scope_bullets: List of child skills to guide question scope (3-6 items)
        model: Model name
        
    Returns:
        Parsed MCQ dict with keys: question_text, options, correct_option, explanation, difficulty, skill
        
    Raises:
        ValueError: If generation fails after retries (non-fatal, caller should continue)
    """
    # Build scope section
    scope_text = "\n".join([f"- {bullet}" for bullet in scope_bullets[:6]])
    
    prompt = f"""Return ONLY JSON. No extra text.

Generate a {difficulty} difficulty multiple-choice question.

Skill: {skill_name}

Focus on:
{scope_text}

Required JSON keys:
- skill: "{skill_name}"
- difficulty: "{difficulty}"
- question_text: (string, the question)
- options: (object with A, B, C, D as keys, string values)
- correct_option: (one of: A, B, C, D)
- explanation: (1-2 sentences why correct answer is right)

Rules:
- Exactly one correct answer
- Avoid "All of the above"
- Avoid ambiguous questions
- Question must relate to the focus topics"""

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(
            f"Generating MCQ for skill={skill_name}, difficulty={difficulty}, "
            f"attempt={attempt}/{MAX_RETRIES}"
        )
        
        try:
            # Call Ollama
            ollama_response = call_ollama(prompt, model)
            response_text = ollama_response.get("response", "").strip()
            
            if not response_text:
                logger.warning(f"Empty response on attempt {attempt}")
                continue
            
            # Parse JSON with loose parser
            mcq_data = parse_json_loose(response_text)
            
            # Validate required fields
            required_keys = ["question_text", "options", "correct_option", "explanation"]
            missing = [k for k in required_keys if k not in mcq_data]
            if missing:
                logger.warning(f"Missing keys: {missing}, retrying...")
                continue
            
            # Ensure difficulty and skill are set correctly
            mcq_data["difficulty"] = difficulty
            mcq_data["skill"] = skill_name
            
            # Validate options structure
            if not isinstance(mcq_data["options"], dict):
                logger.warning("Options is not a dict, retrying...")
                continue
            
            required_options = ["A", "B", "C", "D"]
            if not all(opt in mcq_data["options"] for opt in required_options):
                logger.warning("Missing required options A-D, retrying...")
                continue
            
            # Validate correct_option
            if mcq_data["correct_option"] not in required_options:
                logger.warning(f"Invalid correct_option: {mcq_data['correct_option']}, retrying...")
                continue
            
            logger.info(
                f"Successfully generated MCQ for skill={skill_name}, difficulty={difficulty}"
            )
            return mcq_data
            
        except ValueError as e:
            logger.warning(f"JSON parse error on attempt {attempt}: {str(e)}")
            if attempt == MAX_RETRIES:
                logger.error(f"Final parse error for {skill_name}/{difficulty}")
            continue
        except HTTPException as e:
            # Network/Ollama error - propagate immediately
            raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt}: {str(e)}")
            if attempt == MAX_RETRIES:
                raise ValueError(f"Failed after {MAX_RETRIES} attempts: {str(e)}")
            continue
    
    # All retries failed - raise ValueError (non-fatal)
    error_msg = f"Failed to generate valid MCQ for skill '{skill_name}', difficulty '{difficulty}' after {MAX_RETRIES} attempts"
    logger.error(error_msg)
    raise ValueError(error_msg)
