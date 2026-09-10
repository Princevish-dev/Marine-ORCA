def critic_agent(state: dict) -> dict:
    weather_data = state.get("weather_data") or {}
    pfz_score = state.get("pfz_score", 0)
    messages = list(state.get("messages") or [])
    is_safe = state.get("is_safe", True)
    severity = weather_data.get("severity", 0)

    if severity >= 3:
        pfz_score = 0
        is_safe = False

        messages.append({
            "role": "system",
            "priority": "high",
            "content": (
                "CRITICAL WARNING: Severe weather detected. Safety overrides "
                "PFZ suitability and marine activity is not safe."
            ),
        })

    return {
        "weather_data": weather_data,
        "pfz_score": pfz_score,
        "is_safe": is_safe,
        "messages": messages
    }
