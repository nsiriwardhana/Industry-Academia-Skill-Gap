"""
Unified backend entry point.

Run this file once to serve both the login backend and Nipuni backend from a
single API base URL.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response


BASE_DIR = Path(__file__).resolve().parent
LOGIN_DIR = BASE_DIR / "login"
NIPUNI_DIR = BASE_DIR / "Nipuni_backend" / "src"
NILMANI_DIR = BASE_DIR / "Nilmani-backend"
ADVANCED_RECOMMENDATION_DIR = BASE_DIR / "Advanced-Recommendation-System"
AGENT_RUNTIME_DIR = BASE_DIR / "Agent-Runtime"
THISARAVI_DIR = BASE_DIR / "Thisaravi-Backend"

LOGIN_INTERNAL_PORT = int(os.getenv("LOGIN_INTERNAL_PORT", "8182"))
NIPUNI_INTERNAL_PORT = int(os.getenv("NIPUNI_INTERNAL_PORT", "8181"))
NILMANI_INTERNAL_PORT = int(os.getenv("NILMANI_INTERNAL_PORT", "8183"))
ADVANCED_RECOMMENDATION_INTERNAL_PORT = int(os.getenv("ADVANCED_RECOMMENDATION_INTERNAL_PORT", "8184"))
AGENT_RUNTIME_INTERNAL_PORT = int(os.getenv("AGENT_RUNTIME_INTERNAL_PORT", "8185"))
THISARAVI_INTERNAL_PORT = int(os.getenv("THISARAVI_INTERNAL_PORT", "8186"))
PUBLIC_PORT = int(os.getenv("PORT", "8000"))
PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", f"http://localhost:{PUBLIC_PORT}")
BOOT_TIMEOUT_SECONDS = float(os.getenv("MERGED_BOOT_TIMEOUT_SECONDS", "60"))
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("MERGED_UPSTREAM_TIMEOUT_SECONDS", "120"))

LOGIN_BASE_URL = f"http://127.0.0.1:{LOGIN_INTERNAL_PORT}"
NIPUNI_BASE_URL = f"http://127.0.0.1:{NIPUNI_INTERNAL_PORT}"
NILMANI_BASE_URL = f"http://127.0.0.1:{NILMANI_INTERNAL_PORT}"
ADVANCED_RECOMMENDATION_BASE_URL = f"http://127.0.0.1:{ADVANCED_RECOMMENDATION_INTERNAL_PORT}"
AGENT_RUNTIME_BASE_URL = f"http://127.0.0.1:{AGENT_RUNTIME_INTERNAL_PORT}"
THISARAVI_BASE_URL = f"http://127.0.0.1:{THISARAVI_INTERNAL_PORT}"

HOP_BY_HOP_HEADERS = {
	"connection",
	"keep-alive",
	"proxy-authenticate",
	"proxy-authorization",
	"te",
	"trailers",
	"transfer-encoding",
	"upgrade",
}


@dataclass
class BackendProcess:
	name: str
	port: int
	working_dir: Path
	health_path: str
	process: Optional[subprocess.Popen] = None

	@property
	def base_url(self) -> str:
		return f"http://127.0.0.1:{self.port}"


BACKENDS: Dict[str, BackendProcess] = {
	"login": BackendProcess(
		name="login",
		port=LOGIN_INTERNAL_PORT,
		working_dir=LOGIN_DIR,
		health_path="/health",
	),
	"nipuni": BackendProcess(
		name="nipuni",
		port=NIPUNI_INTERNAL_PORT,
		working_dir=NIPUNI_DIR,
		health_path="/health",
	),
	"nilmani": BackendProcess(
		name="nilmani",
		port=NILMANI_INTERNAL_PORT,
		working_dir=NILMANI_DIR,
		health_path="/health",
	),
	"advanced_recommendation": BackendProcess(
		name="advanced_recommendation",
		port=ADVANCED_RECOMMENDATION_INTERNAL_PORT,
		working_dir=ADVANCED_RECOMMENDATION_DIR,
		health_path="/",
	),
	"agent_runtime": BackendProcess(
		name="agent_runtime",
		port=AGENT_RUNTIME_INTERNAL_PORT,
		working_dir=AGENT_RUNTIME_DIR,
		health_path="/health",
	),
	"thisaravi": BackendProcess(
		name="thisaravi",
		port=THISARAVI_INTERNAL_PORT,
		working_dir=THISARAVI_DIR,
		health_path="/health",
	),
}


app = FastAPI(
	title="Unified Project Integration API",
	description="Single entry point that serves login and Nipuni backend APIs.",
	version="1.0.0",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:3000",
		"http://localhost:3001",
		"http://localhost:5173",
		"http://localhost:4173",
		"http://localhost:8080",
		"http://localhost:8081",
		"http://localhost:8082",
		"http://localhost:8001",
	    "http://localhost:8002",
	    "http://localhost:8010",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


def _start_backend(backend: BackendProcess) -> None:
	if not backend.working_dir.exists():
		raise RuntimeError(f"Backend directory not found: {backend.working_dir}")

	command = [
		sys.executable,
		"-m",
		"uvicorn",
		"app.main:app",
		"--host",
		"127.0.0.1",
		"--port",
		str(backend.port),
		"--log-level",
		"warning",
	]

	env = os.environ.copy()
	env.setdefault("PYTHONUNBUFFERED", "1")
	if backend.name == "login":
		# Ensure OAuth callback and generated backend URLs point to unified API.
		env.setdefault("BACKEND_URL", PUBLIC_BACKEND_URL)

	backend.process = subprocess.Popen(
		command,
		cwd=str(backend.working_dir),
		env=env,
	)


def _stop_backend(backend: BackendProcess) -> None:
	if backend.process is None:
		return

	if backend.process.poll() is None:
		backend.process.terminate()
		try:
			backend.process.wait(timeout=10)
		except subprocess.TimeoutExpired:
			backend.process.kill()
			backend.process.wait(timeout=5)


async def _wait_until_ready(backend: BackendProcess, timeout_seconds: float) -> None:
	if backend.process is None:
		raise RuntimeError(f"Backend process not started: {backend.name}")

	deadline = time.monotonic() + timeout_seconds
	health_url = f"{backend.base_url}{backend.health_path}"

	async with httpx.AsyncClient(timeout=2.0) as client:
		while time.monotonic() < deadline:
			if backend.process.poll() is not None:
				raise RuntimeError(
					f"Backend '{backend.name}' exited early with code {backend.process.returncode}."
				)

			try:
				response = await client.get(health_url)
				if response.status_code < 500:
					return
			except httpx.HTTPError:
				pass

			await asyncio.sleep(0.5)

	raise RuntimeError(f"Backend '{backend.name}' did not become ready at {health_url}.")


def _resolve_target(path: str) -> tuple[str, str]:
	# Nilmani aliases for endpoints that would otherwise conflict with unified root paths.
	if path == "/nilmani":
		return NILMANI_BASE_URL, "/"

	if path.startswith("/nilmani/"):
		rewritten_path = path[len("/nilmani") :]
		if not rewritten_path:
			rewritten_path = "/"
		return NILMANI_BASE_URL, rewritten_path

	# Advanced Recommendation System endpoints
	if path.startswith("/candidates") or path.startswith("/xai") or path.startswith("/cache"):
		return ADVANCED_RECOMMENDATION_BASE_URL, path

	if path.startswith("/roles/") or (path.startswith("/roles") and len(path) > 6 and path[6] in "?"):
		return ADVANCED_RECOMMENDATION_BASE_URL, path

	# Agent Runtime endpoints
	if path.startswith("/job-gap") or path.startswith("/agent") or path.startswith("/test") or path.startswith("/runtime") or path.startswith("/explain") or path.startswith("/aliases"):
		return AGENT_RUNTIME_BASE_URL, path

	# Thisaravi endpoints (checked after more specific patterns)
	if (path.startswith("/generate-project") or path.startswith("/submit-feedback") or 
	    path.startswith("/unreviewed-outputs") or path.startswith("/feedback") or
	    path.startswith("/pattern-reports") or path.startswith("/preview-evolution") or
	    path.startswith("/apply-evolution") or path.startswith("/prompt-evolutions") or
	    path.startswith("/current-prompt") or path.startswith("/run-regeneration") or
	    path.startswith("/list-datasets") or path.startswith("/upload-to-hf") or
	    path.startswith("/jobs-by-role") or path.startswith("/search-jobs") or
	    path.startswith("/my-outputs") or path.startswith("/run-analysis") or path == "/roles"):
		return THISARAVI_BASE_URL, path

	# Preserve both admin APIs by routing Nipuni-specific admin paths first.
	if path.startswith("/admin/question-bank") or path.startswith("/admin/seed-mapping"):
		return NIPUNI_BASE_URL, path

	login_prefixes = ("/auth", "/candidate", "/admin")
	if path.startswith(login_prefixes):
		return LOGIN_BASE_URL, path

	# Nilmani interview API endpoints
	if path.startswith("/api"):
		return NILMANI_BASE_URL, path

	return NIPUNI_BASE_URL, path


def _prepare_forward_headers(request: Request) -> Dict[str, str]:
	headers = dict(request.headers)
	headers.pop("host", None)
	headers.pop("content-length", None)
	return headers


def _prepare_response_headers(headers: httpx.Headers) -> Dict[str, str]:
	prepared: Dict[str, str] = {}
	for key, value in headers.items():
		if key.lower() not in HOP_BY_HOP_HEADERS:
			prepared[key] = value
	return prepared


@app.on_event("startup")
async def startup_event() -> None:
	try:
		_start_backend(BACKENDS["login"])
		_start_backend(BACKENDS["nipuni"])
		_start_backend(BACKENDS["nilmani"])
		_start_backend(BACKENDS["advanced_recommendation"])
		_start_backend(BACKENDS["agent_runtime"])
		_start_backend(BACKENDS["thisaravi"])
		await asyncio.gather(
			_wait_until_ready(BACKENDS["login"], BOOT_TIMEOUT_SECONDS),
			_wait_until_ready(BACKENDS["nipuni"], BOOT_TIMEOUT_SECONDS),
			_wait_until_ready(BACKENDS["nilmani"], BOOT_TIMEOUT_SECONDS),
			_wait_until_ready(BACKENDS["advanced_recommendation"], BOOT_TIMEOUT_SECONDS),
			_wait_until_ready(BACKENDS["agent_runtime"], BOOT_TIMEOUT_SECONDS),
			_wait_until_ready(BACKENDS["thisaravi"], BOOT_TIMEOUT_SECONDS),
		)
	except Exception:
		for backend in BACKENDS.values():
			_stop_backend(backend)
		raise


@app.on_event("shutdown")
async def shutdown_event() -> None:
	for backend in BACKENDS.values():
		_stop_backend(backend)


@app.get("/")
async def root() -> Dict[str, object]:
	return {
		"message": "Unified backend is running",
		"version": "1.0.0",
		"docs": "/docs",
		"backends": {
			"login": {"base_url": LOGIN_BASE_URL, "health": "/health"},
			"nipuni": {"base_url": NIPUNI_BASE_URL, "health": "/health"},
			"nilmani": {"base_url": NILMANI_BASE_URL, "health": "/health"},
			"advanced_recommendation": {"base_url": ADVANCED_RECOMMENDATION_BASE_URL, "health": "/"},
			"agent_runtime": {"base_url": AGENT_RUNTIME_BASE_URL, "health": "/health"},
			"thisaravi": {"base_url": THISARAVI_BASE_URL, "health": "/health"},
		},
		"endpoints": {
			"login_auth": {
				"login": "/auth/login/google",
				"callback": "/auth/google/callback",
				"current_user": "/auth/me",
				"logout": "/auth/logout",
				"health": "/auth/health",
			},
			"login_candidate": {
				"init": "POST /candidate/init",
				"status": "GET /candidate/{candidate_id}/status",
				"my_profile": "GET /candidate/me",
				"delete": "DELETE /candidate/me",
				"health": "GET /candidate/health",
			},
			"nipuni_skill_validation": {
				"upload_transcript": "POST /transcript/upload",
				"claimed_skills": "GET /students/{student_id}/skills/claimed",
				"quiz_plan": "POST /students/{student_id}/quiz/plan",
				"job_recommend": "GET /students/{student_id}/jobs/recommend",
				"job_recommend_ml": "GET /students/{student_id}/jobs/recommend/ml",
			},
			"nilmani_interview": {
				"upload_jd": "POST /api/upload-jd",
				"start_interview": "POST /api/start-interview",
				"next_question": "POST /api/next-question",
				"session_status": "GET /api/session/{session_id}",
				"end_session": "DELETE /api/session/{session_id}",
				"list_sessions": "GET /api/sessions",
				"health_alias": "GET /nilmani/health",
				"root_alias": "GET /nilmani",
			},
			"advanced_recommendation_roles": {
				"list_roles": "GET /roles",
				"role_skill_profile": "GET /roles/{role_key}/skill-profile",
				"role_category_profile": "GET /roles/{role_key}/category-profile",
			},
			"advanced_recommendation_candidates": {
				"skill_confidence": "GET /candidates/{candidate_id}/skill-confidence",
				"skill_gap_advanced": "GET /candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced",
				"course_recommendations": "GET /candidates/{candidate_id}/roles/{role_key}/recommendations",
				"course_job_gap": "POST /candidates/{candidate_id}/courses/recommend-for-job-gap",
				"project_relevance": "GET /candidates/{candidate_id}/roles/{role_key}/project-relevance",
				"missing_skills_gnn": "GET /candidates/{candidate_id}/roles/{role_key}/missing-skills-gnn",
			},
			"advanced_recommendation_xai": {
				"skill_explanation": "GET /xai/missing-skill",
				"xai_health": "GET /xai/health",
			},
			"advanced_recommendation_admin": {
				"cache_clear": "GET /cache/clear",
			},
			"agent_runtime_job_gap": {
				"analyze_gap": "POST /job-gap/analyze",
				"extract_jd": "POST /job-gap/extract",
				"get_job": "GET /job-gap/{job_id}",
				"delete_job": "DELETE /job-gap/{job_id}",
				"list_jobs": "GET /job-gap",
			},
			"agent_runtime_core": {
				"run_agent": "POST /agent/run",
				"run_agent_from_pdf": "POST /agent/run-from-pdf",
			},
			"agent_runtime_explainability": {
				"skill_explain": "GET /runtime/skill-explain",
				"predict_explain": "GET /runtime/predict-explain",
				"predict_explain_legacy": "GET /runtime/predict-explain-legacy",
			},
			"agent_runtime_testing": {
				"extract_from_text": "POST /test/extract-from-text",
				"normalize_skills": "POST /test/normalize-skills",
				"complete_pipeline": "POST /test/complete-pipeline",
			},
			"agent_runtime_explain_routes": {
				"explain": "POST /explain",
				"explain_health": "GET /explain/health",
				"explain_info": "GET /explain/info",
			},
			"agent_runtime_utilities": {
				"get_aliases": "GET /aliases",
				"add_alias": "POST /aliases/add",
			},
			"thisaravi_project_generation": {
				"generate_project": "POST /generate-project",
				"generate_project_from_sources": "POST /generate-project-from-sources",
				"list_roles": "GET /roles",
			},
			"thisaravi_feedback": {
				"submit_feedback": "POST /submit-feedback",
				"get_unreviewed": "GET /unreviewed-outputs",
				"feedback_status": "GET /feedback-status",
				"all_feedback": "GET /all-feedback",
				"my_outputs": "GET /my-outputs",
			},
			"thisaravi_analysis": {
				"run_analysis": "POST /run-analysis",
				"pattern_reports": "GET /pattern-reports",
			},
			"thisaravi_evolution": {
				"preview_evolution": "POST /preview-evolution",
				"apply_evolution": "POST /apply-evolution",
				"prompt_evolutions": "GET /prompt-evolutions",
				"current_prompt": "GET /current-prompt",
				"run_regeneration": "POST /run-regeneration",
			},
			"thisaravi_datasets": {
				"list_datasets": "GET /list-datasets",
				"upload_to_hf": "POST /upload-to-hf",
			},
			"thisaravi_jobs": {
				"jobs_by_role": "GET /jobs-by-role",
				"search_jobs": "GET /search-jobs",
			},
		},
		"routing": {
			"login": ["/auth/*", "/candidate/*", "/admin/*"],
			"nipuni": ["/transcript/*", "/students/*", "/jobs/*", "/health"],
			"nipuni_admin": ["/admin/question-bank/*", "/admin/seed-mapping"],
			"nilmani": ["/api/*", "/nilmani", "/nilmani/*"],
"advanced_recommendation": ["/roles/{role_key}/*", "/candidates/*", "/cache/*", "/xai/*"],
		"agent_runtime": ["/job-gap/*", "/agent/*", "/runtime/*", "/test/*", "/explain/*", "/aliases/*"],
		"thisaravi": ["/generate-project*", "/submit-feedback*", "/feedback*", "/evolution*", "/regeneration*", "/analysis*", "/datasets*", "/jobs*", "/search*", "/unreviewed*", "/pattern*", "/preview*", "/apply*", "/roles"],
		},
	}


@app.get("/health")
async def health() -> Dict[str, object]:
	results: Dict[str, object] = {}

	async with httpx.AsyncClient(timeout=3.0) as client:
		for backend in BACKENDS.values():
			process_alive = backend.process is not None and backend.process.poll() is None
			health_url = f"{backend.base_url}{backend.health_path}"

			if not process_alive:
				results[backend.name] = {
					"process": "down",
					"upstream": "unreachable",
				}
				continue

			try:
				response = await client.get(health_url)
				results[backend.name] = {
					"process": "up",
					"upstream": "healthy" if response.status_code < 500 else "degraded",
					"status_code": response.status_code,
				}
			except httpx.HTTPError:
				results[backend.name] = {
					"process": "up",
					"upstream": "unreachable",
				}

	overall = "healthy"
	for backend_state in results.values():
		if backend_state.get("process") != "up" or backend_state.get("upstream") == "unreachable":
			overall = "degraded"
			break

	return {
		"status": overall,
		"service": "unified-backend",
		"backends": results,
	}


@app.api_route(
	"/{full_path:path}",
	methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(full_path: str, request: Request) -> Response:
	path = f"/{full_path}"
	target_base, upstream_path = _resolve_target(path)

	query_string = request.url.query
	target_url = f"{target_base}{upstream_path}"
	if query_string:
		target_url = f"{target_url}?{query_string}"

	try:
		body = await request.body()
		async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS, follow_redirects=False) as client:
			upstream_response = await client.request(
				method=request.method,
				url=target_url,
				headers=_prepare_forward_headers(request),
				content=body,
				cookies=request.cookies,
			)
	except httpx.RequestError as exc:
		return JSONResponse(
			status_code=502,
			content={
				"detail": "Failed to contact upstream backend",
				"target": target_base,
				"error": str(exc),
			},
		)

	return Response(
		content=upstream_response.content,
		status_code=upstream_response.status_code,
		headers=_prepare_response_headers(upstream_response.headers),
	)


if __name__ == "__main__":
	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=PUBLIC_PORT,
		reload=False,
		log_level="info",
	)
