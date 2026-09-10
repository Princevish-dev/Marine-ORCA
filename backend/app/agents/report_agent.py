from app.models import OrcaState
from app.services.ollama import generate_local_context
from app.agents.utils import start_stage, complete_stage, llm_call

def report_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    s = start_stage(s, "report", "Report Agent")

    try:
        if s.intent == "conversation":
            greetings = {
                "hi": "Hello! I am ORCA. Ask me about marine safety, weather, fishing zones, or routes.",
                "hello": "Hello! I am ORCA. How can I help with your marine query?",
                "hey": "Hey! Ask ORCA about marine safety, weather, PFZs, or routes.",
            }
            answer = greetings.get(s.query.strip().lower(), "Hello! How can I help with your marine query?")
            s.final_answer = answer
            s = complete_stage(
                s,
                "report",
                source="ORCA Conversation Router",
                summary="Greeting response generated",
            )
            return s.model_dump()

        safety = s.safety_result
        weather = s.weather_result
        marine = s.marine_result
        lang = s.language

        context_lines = [f"User query: {s.query}"]
        if safety:
            context_lines.append(f"Safety score: {safety.score}/100 ({safety.label})")
            context_lines.append(f"Safety explanation: {safety.explanation}")
        if weather:
            context_lines.append(f"Wind: {weather.wind_speed_kmh:.0f} km/h, Condition: {weather.weather_condition}")
        if marine:
            context_lines.append(f"Wave height: {marine.wave_height_m:.1f} m, Period: {marine.wave_period_s:.1f} s")
        if s.ocean_result and getattr(s.ocean_result, "sst_anomaly", None):
            if s.ocean_result.sst_anomaly > 1.5:
                context_lines.append(f"SST Anomaly: +{s.ocean_result.sst_anomaly:.1f}°C (MIGRATION_LIKELY)")
        if s.geo_result:
            context_lines.append(f"Boundary status: {s.geo_result.status} ({s.geo_result.distance_km} km)")
            if getattr(s.geo_result, "esz_proximity", False):
                context_lines.append("Ecological Sensitive Zone nearby: applying ecological penalty.")
        if s.pfz_result:
            top = s.pfz_result[0]
            context_lines.append(f"Nearest PFZ: {top.distance_km} km away (score {top.score}/100)")
            if top.stock_depletion_risk:
                context_lines.append("STOCK DEPLETION RISK: Historical catch density is too low. Recommend CONSERVE.")
        if s.route_result:
            context_lines.append(
                f"ORCA route: {s.route_result.orca_distance_km} km "
                f"(vs direct {s.route_result.direct_distance_km} km), "
                f"modelled fuel saving {s.route_result.fuel_reduction_pct}%"
            )
        if s.collective_impact_result:
            ci = s.collective_impact_result
            if ci.collective_pressure_warning:
                context_lines.append("COLLECTIVE IMPACT ADVISORY:")
                context_lines.append(f"  Pressure warning: YES")
                context_lines.append(f"  Avoided zones (HIGH congestion): {', '.join(ci.avoided_zones)}")
                context_lines.append(f"  Recommended zones (diversified): {', '.join(ci.diversified_zones[:3])}")
                context_lines.append(f"  {ci.redistribution_note}")
                context_lines.append("  ORCA doesn't just find the best fishing spot. It prevents the AI from creating the next fishing hotspot.")
            else:
                context_lines.append("Collective Impact: No fleet congestion detected. All zones have safe vessel density.")
        local_context = generate_local_context(
            s.query,
            s.session_context.get("history", []),
        )
        if local_context:
            context_lines.append(f"Local Ollama context, continuity only: {local_context}")
        context = "\n".join(context_lines)
        is_demo = any([
            getattr(s.weather_result, "is_demo", False),
            getattr(s.marine_result, "is_demo", False),
        ])

        lang_instruction = {
            "hi": "Respond in Hindi (Devanagari script). Keep source names in English.",
            "bn": "Respond in Bengali.",
            "ta": "Respond in Tamil.",
            "te": "Respond in Telugu.",
            "mr": "Respond in Marathi.",
            "gu": "Respond in Gujarati.",
            "kn": "Respond in Kannada.",
        }.get(lang, "Respond in English.")

        system_prompt = f"""You are ORCA, a professional marine decision-support AI.
Generate a clear, structured response based ONLY on the provided data. Do NOT invent any numbers.
Use professional marine terminology. Mention evidence sources.
{lang_instruction}
{"NOTE: Data is from DEMO FIXTURES — clearly state this." if is_demo else ""}
If safety score < 50, recommend caution clearly. If score >= 80, state conditions look favorable.
Format: Brief assessment paragraph, then key conditions list, then recommendation."""

        answer = llm_call(context, system_prompt)

        if "[Ollama unavailable]" in answer or not answer.strip():
            if safety:
                if safety.score >= 80:
                    status_word = "favorable" if lang == "en" else "अनुकूल" if lang == "hi" else "favorable"
                elif safety.score >= 60:
                    status_word = "moderate with caution advised"
                else:
                    status_word = "hazardous — avoid if possible"
                answer = (
                    f"ORCA Assessment — Safety: {safety.score}/100 ({safety.label})\n\n"
                    f"Conditions appear {status_word}.\n\n"
                    f"{safety.explanation}\n\n"
                    + (f"Wind: {weather.wind_speed_kmh:.0f} km/h | " if weather else "")
                    + (f"Waves: {marine.wave_height_m:.1f} m\n\n" if marine else "")
                    + "Verify latest official marine warnings before departure."
                )
            else:
                answer = "ORCA could not complete the full assessment. Please retry."

        s.final_answer = answer
        s = complete_stage(s, "report", source="Ollama + ORCA Evidence Engine",
                             summary="Response generated successfully")
    except Exception as exc:
        s.final_answer = "ORCA could not complete the reasoning workflow. Please retry."
        s = complete_stage(s, "report", summary=f"Error: {exc}", error=True)

    if s.trace.stages:
        first = next((st.started_at for st in s.trace.stages if st.started_at), None)
        last = max((st.completed_at for st in s.trace.stages if st.completed_at), default=None)
        if first and last:
            s.trace.total_duration_ms = (last - first).total_seconds() * 1000

    return s.model_dump()
