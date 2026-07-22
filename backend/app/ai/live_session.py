from datetime import datetime


LIVE_AI_SESSION = {
    "active": False,
    "phase": "Ready",
    "round": 0,
    "total_rounds": 0,
    "time_left": 0,
    "module": "TNG Coach AI",
    "prompt": "Waiting for coach to start session",
    "sub_prompt": "Open this screen on every TV in the gym.",
    "updated_at": datetime.utcnow().isoformat(),
}
