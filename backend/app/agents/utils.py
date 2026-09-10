from datetime import datetime, timezone
from app.models import OrcaState, TraceStage
from app.services.ollama import generate_ollama_response

def llm_call(prompt: str, system: str = "") -> str:
    return generate_ollama_response(prompt, system) or "[Ollama unavailable]"

def start_stage(state: OrcaState, stage_id: str, name: str) -> OrcaState:
    stage = TraceStage(id=stage_id, name=name, status="RUNNING", started_at=datetime.now(timezone.utc))
    state.trace.stages.append(stage)
    return state

def complete_stage(
    state: OrcaState, stage_id: str,
    source: str = "", summary: str = "",
    confidence: float = 1.0, warning: str = "", error: bool = False,
) -> OrcaState:
    for st in state.trace.stages:
        if st.id == stage_id:
            st.status = "ERROR" if error else "COMPLETED"
            st.completed_at = datetime.now(timezone.utc)
            if st.started_at:
                st.duration_ms = (st.completed_at - st.started_at).total_seconds() * 1000
            st.source = source
            st.result_summary = summary
            st.confidence = confidence
            st.warning = warning or None
    return state

def skip_stage(state: OrcaState, stage_id: str, name: str) -> OrcaState:
    stage = TraceStage(id=stage_id, name=name, status="SKIPPED")
    state.trace.stages.append(stage)
    return state
