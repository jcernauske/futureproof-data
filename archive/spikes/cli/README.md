# Archived CLI Spike

This folder contains the original FutureProof interactive CLI proof of concept.

Status: deprecated. The CLI was used to prove the Gemma + public-data workflow before the web product existed. It is not the canonical implementation for the Kaggle Gemma 4 Good submission.

Canonical path:

- Backend API and services under `backend/app/`
- Web UI under `frontend/`
- Set Your Course / intent flow in `backend/app/services/set_your_course.py`
- Current non-streaming intent service in `backend/app/services/intent.py`

Notes:

- Prompts and UX behavior in `cli.py` may be stale relative to the web/API flow.
- Do not use this CLI for demo videos, judge instructions, or submission reproducibility.
- Keep it here only as historical implementation context.
