"""
Interview Engine Module
Orchestrates the RAG-based interview process:
1. Retrieves relevant JD chunks from FAISS (using LOCAL Ollama embeddings)
2. Generates questions using Google Gemini (text generation only)
3. Evaluates answer correctness for feedback summaries
"""
from __future__ import annotations

import json
import logging

from app.core.config import MAX_QUESTIONS
from app.interview_gemini.llm.gemini import get_llm, generate_text
from app.interview_gemini.llm.prompt import INTERVIEW_PROMPT, STRICT_FEEDBACK_PROMPT
from app.interview_gemini.rag.retriever import retrieve_context

logger = logging.getLogger(__name__)

# Initialize Gemini LLM (for text generation only)
llm = get_llm()


def _build_evaluation_prompt(question: str, answer: str, context: str) -> str:
    return f"""
You are evaluating a candidate's answer to a job interview question.

Return ONLY valid JSON with these keys:
- score: integer from 0 to 100
- feedback: concise constructive feedback in 2-3 sentences
- reasoning: one short sentence explaining the score

Question:
{question}

Candidate Answer:
{answer}

Job Description Context:
{context}

Scoring guidance:
- 90-100: excellent and highly relevant
- 70-89: good but missing minor details
- 40-69: partially correct, incomplete, or weakly supported
- 0-39: mostly incorrect or irrelevant

Return JSON only.
"""


def _parse_json_response(raw_text: str) -> dict:
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    # First, try strict JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.debug("Strict json.loads failed, trying tolerant parsing")

    # Try to extract JSON-looking substring
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
    else:
        candidate = text

    # Try json5 if available (supports single quotes, trailing commas, unquoted keys)
    try:
        import json5  # type: ignore

        try:
            return json5.loads(candidate)
        except Exception:
            logger.debug("json5.loads failed on candidate JSON")
    except Exception:
        logger.debug("json5 not available; falling back to ast.literal_eval")

    # As a last resort, try ast.literal_eval which can handle Python-style dicts
    try:
        import ast

        parsed = ast.literal_eval(candidate)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        logger.debug("ast.literal_eval failed to parse candidate JSON")

    # Log the raw response for debugging and raise a clear error
    logger.error("Failed to parse JSON response from LLM. Raw response:\n%s", text)
    raise json.JSONDecodeError("Unable to parse JSON response", text, 0)


def evaluate_answer(question: str, answer: str, vector_store) -> dict:
    query = f"skills, responsibilities, and requirements related to: {question}"
    context = retrieve_context(vector_store, query=query, k=4)

    if not context:
        context = "No specific job description context available."

    # Use strict JSON prompt with example to encourage valid JSON output
    prompt = STRICT_FEEDBACK_PROMPT + f"\nQuestion:\n{question}\n\nCandidate Answer:\n{answer}\n\nJob Description Context:\n{context}\n"

    try:
        raw_response = generate_text(llm, prompt)
        parsed = _parse_json_response(raw_response)
    except Exception as e:
        logger.warning("Initial parsing failed: %s. Retrying with explicit JSON-only reminder.", str(e))
        # Retry once with an explicit short JSON-only instruction
        retry_prompt = (
            prompt
            + "\n\nIMPORTANT: Return ONLY valid JSON exactly matching the schema and nothing else."
        )
        try:
            raw_response = generate_text(llm, retry_prompt)
            parsed = _parse_json_response(raw_response)
        except Exception as e2:
            # Log full LLM outputs and return a safe default evaluation to avoid 500s
            logger.error("Failed to parse evaluation JSON after retry. Last error: %s", str(e2))
            logger.error("Last raw response: %s", raw_response if 'raw_response' in locals() else 'NO RESPONSE')
            return {"score": 0, "feedback": "Unable to evaluate answer due to LLM formatting error.", "reasoning": "Parsing failed"}

    score = int(parsed.get("score", 0))
    score = max(0, min(100, score))

    return {
        "score": score,
        "feedback": str(parsed.get("feedback", "")).strip(),
        "reasoning": str(parsed.get("reasoning", "")).strip(),
    }


def generate_next_turn(session: dict, user_answer: str = None) -> tuple:
    """
    Generate next interview turn using RAG approach.

    Process:
    1. Retrieve relevant JD chunks from FAISS (using LOCAL Ollama embeddings)
    2. Send context + history to Gemini for question generation
    3. Update session state

    Args:
        session: Interview session dict containing vector_store, history, etc.
        user_answer: Optional user's answer to previous question

    Returns:
        tuple: (question, feedback, ended)
            - question: Next question or None if ended
            - feedback: Feedback on previous answer or None
            - ended: Boolean indicating if interview has ended

    Raises:
        Exception: If generation fails
    """
    try:
        # Check if interview already ended
        if session.get("ended", False):
            logger.info("Interview already ended")
            return None, None, True

        questions_asked = session.get("questions_asked", 0)
        evaluation = None

        # Add user answer to history and score it
        if user_answer:
            session["history"].append(f"Candidate: {user_answer}")
            logger.debug(f"Added user answer to history: {user_answer[:50]}...")

            current_question = session.get("last_question")
            vector_store = session.get("vector_store")

            if current_question and vector_store:
                evaluation = evaluate_answer(current_question, user_answer, vector_store)
                session.setdefault("evaluations", []).append(
                    {
                        "question": current_question,
                        "answer": user_answer,
                        **evaluation,
                    }
                )
                session.setdefault("answer_scores", []).append(evaluation["score"])
                session["last_evaluation"] = evaluation

            if questions_asked >= MAX_QUESTIONS:
                session["ended"] = True
                logger.info("Final answer evaluated. Ending interview.")
                return None, evaluation["feedback"] if evaluation else None, True

        # Check if max questions reached
        if questions_asked >= MAX_QUESTIONS:
            logger.info(f"Max questions ({MAX_QUESTIONS}) reached. Ending interview.")
            session["ended"] = True
            return None, "Thank you for participating in this interview!", True

        # Retrieve relevant context from JD using RAG
        # This uses LOCAL Ollama embeddings, NOT cloud API
        vector_store = session.get("vector_store")
        if not vector_store:
            raise ValueError("Vector store not found in session")

        context = retrieve_context(
            vector_store,
            query="job responsibilities, required skills, qualifications, and experience",
            k=4,
        )

        if not context:
            logger.warning("No context retrieved from vector store, using empty context")
            context = "No specific job description context available."

        # Build prompt for Gemini
        history_text = "\n".join(session.get("history", []))
        prompt = INTERVIEW_PROMPT.format(
            context=context,
            history=history_text if history_text else "No conversation yet.",
        )

        logger.debug("Sending prompt to Gemini for question generation")

        # Generate response using Gemini (text generation only)
        response = generate_text(llm, prompt)

        # Update session state
        session["questions_asked"] = questions_asked + 1
        session["history"].append(f"Interviewer: {response}")
        session["question_count"] = session["questions_asked"]  # For API compatibility
        session["last_question"] = response

        logger.info(
            f"Generated question {session['questions_asked']}/{MAX_QUESTIONS}"
        )

        feedback = evaluation["feedback"] if evaluation else None
        question = response

        return question, feedback, False

    except Exception as e:
        logger.error(f"Failed to generate next turn: {str(e)}")
        raise Exception(f"Interview generation failed: {str(e)}")


def end_interview(session: dict) -> str:
    """
    End interview session and provide summary.

    Args:
        session: Interview session dict

    Returns:
        str: Interview summary message
    """
    session["ended"] = True
    questions_asked = session.get("questions_asked", 0)

    summary = (
        f"Interview completed. "
        f"You answered {questions_asked} question(s). "
        f"Thank you for your time!"
    )

    logger.info(f"Interview ended: {questions_asked} questions asked")

    return summary
