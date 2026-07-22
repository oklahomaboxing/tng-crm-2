import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.ai.live_session import LIVE_AI_SESSION
from app.ai.models import AIWorkoutRequest
from app.ai.prompts import (
    ALLOWED_LEVELS,
    ALLOWED_MODULES,
    ALLOWED_STANCES,
    SYSTEM_PROMPT,
)
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.models import User
from app.ai.client import client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/ai/training-plan")
def generate_ai_training_plan(
    data: AIWorkoutRequest,
    user: User = Depends(current_user),
):
    require_admin(user)

    if not client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI is not configured on the backend.",
        )

    if data.module not in ALLOWED_MODULES:
        raise HTTPException(
            status_code=400,
            detail="Invalid training module.",
        )

    if data.level not in ALLOWED_LEVELS:
        raise HTTPException(
            status_code=400,
            detail="Invalid training level.",
        )

    if data.stance not in ALLOWED_STANCES:
        raise HTTPException(
            status_code=400,
            detail="Invalid boxing stance.",
        )

    safe_rounds = max(1, min(int(data.rounds), 20))
    safe_round_time = max(30, min(int(data.round_time), 600))
    safe_pace = max(5, min(int(data.pace_seconds), 60))

    commands_per_round = max(
        3,
        min(
            18,
            safe_round_time // safe_pace,
        ),
    )

    user_prompt = f"""
Create a boxing workout using these settings:

Module: {data.module}
Level: {data.level}
Stance: {data.stance}
Rounds: {safe_rounds}
Round duration: {safe_round_time} seconds
Commands per round: approximately {commands_per_round}

Return exactly this JSON structure:

{{
  "title": "Workout title",
  "module": "{data.module}",
  "level": "{data.level}",
  "stance": "{data.stance}",
  "progression_summary": "Short explanation of the workout progression",
  "rounds": [
    {{
      "round_number": 1,
      "module": "Module used during this round",
      "title": "Round title",
      "objective": "Main objective",
      "commands": [
        {{
          "prompt": "Short spoken training command",
          "coaching_cue": "Short technical coaching reminder",
          "objective": "Purpose of the command",
          "opponent_trigger": "Opponent action or situation, or null",
          "correct_exit": "Correct final position or exit"
        }}
      ]
    }}
  ]
}}

Create exactly {safe_rounds} rounds.
Make the rounds progressive rather than random.
"""

    try:
        response = client.chat.completions.create(
            model=os.getenv(
                "OPENAI_TRAINER_MODEL",
                "gpt-4.1-mini",
            ),
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            response_format={
                "type": "json_object",
            },
        )

        raw_content = response.choices[0].message.content

        if not raw_content:
            raise ValueError("OpenAI returned an empty response.")

        workout = json.loads(raw_content)

        generated_rounds = workout.get("rounds")

        if not isinstance(generated_rounds, list):
            raise ValueError(
                "OpenAI response did not include a valid rounds list."
            )

        if len(generated_rounds) != safe_rounds:
            raise ValueError(
                "OpenAI returned the wrong number of rounds."
            )

        return workout

    except json.JSONDecodeError as error:
        logger.exception(
            "AI Trainer returned invalid JSON: %s",
            error,
        )

        raise HTTPException(
            status_code=502,
            detail="OpenAI returned an invalid workout format.",
        )

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "AI Trainer generation failed: %s",
            error,
        )

        raise HTTPException(
            status_code=502,
            detail="The AI workout could not be generated.",
        )


@router.get("/api/ai/live-session")
def get_live_ai_session():
    return LIVE_AI_SESSION


@router.post("/api/ai/live-session")
def update_live_ai_session(
    data: dict,
    user: User = Depends(current_user),
):
    require_admin(user)

    LIVE_AI_SESSION.update(
        {
            "active": data.get(
                "active",
                LIVE_AI_SESSION["active"],
            ),
            "phase": data.get(
                "phase",
                LIVE_AI_SESSION["phase"],
            ),
            "round": data.get(
                "round",
                LIVE_AI_SESSION["round"],
            ),
            "total_rounds": data.get(
                "total_rounds",
                LIVE_AI_SESSION["total_rounds"],
            ),
            "time_left": data.get(
                "time_left",
                LIVE_AI_SESSION["time_left"],
            ),
            "module": data.get(
                "module",
                LIVE_AI_SESSION["module"],
            ),
            "prompt": data.get(
                "prompt",
                LIVE_AI_SESSION["prompt"],
            ),
            "sub_prompt": data.get(
                "sub_prompt",
                LIVE_AI_SESSION["sub_prompt"],
            ),
            "updated_at": datetime.utcnow().isoformat(),
        }
    )

    return LIVE_AI_SESSION