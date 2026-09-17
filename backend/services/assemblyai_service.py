"""
AssemblyAI Service

Handles temporary token generation for the Voice Agent API.
All AssemblyAI-specific authentication and logic is isolated here.
"""

import logging
import requests
from config import Config

logger = logging.getLogger(__name__)

ASSEMBLYAI_TOKEN_URL = "https://agents.assemblyai.com/v1/token"


def generate_temporary_token(expires_in_seconds=300):
    """
    Generate a temporary session token from AssemblyAI.
    Uses Bearer authorization header with ASSEMBLYAI_API_KEY.
    """
    api_key = Config.ASSEMBLYAI_API_KEY
    if not api_key or api_key == "your_assemblyai_api_key_here":
        logger.error("ASSEMBLYAI_API_KEY is missing or unconfigured")
        raise ValueError("ASSEMBLYAI_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        # Request token from AssemblyAI Voice Agent endpoint
        response = requests.get(
            ASSEMBLYAI_TOKEN_URL,
            headers=headers,
            params={"expires_in_seconds": expires_in_seconds},
            timeout=10,
        )

        # Handle 405 Method Not Allowed if endpoint requires POST
        if response.status_code == 405:
            response = requests.post(
                ASSEMBLYAI_TOKEN_URL,
                headers=headers,
                json={"expires_in_seconds": expires_in_seconds},
                timeout=10,
            )

        # Fallback to realtime token endpoint if agents token endpoint returns 404
        if response.status_code == 404:
            alt_url = "https://api.assemblyai.com/v2/realtime/token"
            alt_headers = {"Authorization": api_key, "Content-Type": "application/json"}
            response = requests.post(
                alt_url,
                headers=alt_headers,
                json={"expires_in": expires_in_seconds},
                timeout=10,
            )

        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            if token:
                return token
            raise ValueError("AssemblyAI response missing 'token' field")

        logger.error(
            "AssemblyAI token request failed with status code %s", response.status_code
        )
        raise RuntimeError(f"AssemblyAI API returned status {response.status_code}")

    except requests.RequestException as exc:
        logger.error("Network error communicating with AssemblyAI: %s", exc)
        raise RuntimeError("Failed to communicate with AssemblyAI API")
