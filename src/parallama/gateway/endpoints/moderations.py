"""OpenAI-compatible moderations endpoint implementation."""

from typing import Dict, Any, List, Union
from fastapi import Request
from fastapi.responses import JSONResponse
import re

from ..config import OpenAIConfig

class ModerationsHandler:
    """Handler for moderations endpoint."""

    def __init__(self, config: OpenAIConfig):
        """Initialize moderations handler.
        
        Args:
            config: Gateway configuration
        """
        self.config = config
        # Simple regex patterns for demonstration
        # In production, this would use more sophisticated models/rules
        self.patterns = {
            "hate": r"\b(hate|racist|bigot|discriminat\w+)\b",
            "hate/threatening": r"\b(kill|murder|hurt|harm|attack)\b",
            "self-harm": r"\b(suicide|self-harm|cut\w* (myself|yourself))\b",
            "sexual": r"\b(sex|porn|explicit|nsfw)\b",
            "sexual/minors": r"\b(child|minor|underage).+\b(sex|porn|explicit)\b",
            "violence": r"\b(violen\w+|fight\w*|blood|gore)\b",
            "violence/graphic": r"\b(gore|brutal|graphic|dismember)\b"
        }
        self.score_thresholds = {
            category: 0.5 for category in self.patterns
        }

    async def handle_request(self, request: Request) -> JSONResponse:
        """Handle moderations request.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            JSONResponse: The moderations response
        """
        if not self.config.endpoints.moderations:
            return JSONResponse(
                status_code=404,
                content={"error": "Moderations endpoint is not enabled"}
            )

        data = await request.json()
        validation_error = await self.validate_request(data)
        if validation_error:
            return JSONResponse(
                status_code=400,
                content=validation_error
            )

        input_texts = data.get("input", [])
        if isinstance(input_texts, str):
            input_texts = [input_texts]

        # Count tokens if enabled
        total_tokens = 0
        if self.config.token_counter.enabled:
            for text in input_texts:
                try:
                    tokens = await request.app.state.token_counter.count_tokens(
                        text,
                        "text-moderation-latest"
                    )
                    # Handle mock token counter in tests
                    total_tokens += int(tokens) if isinstance(tokens, (int, float)) else 0
                except (TypeError, ValueError):
                    # Handle any token counting errors
                    continue

        # Process each input text
        results = []
        for text in input_texts:
            result = self._analyze_text(text)
            results.append(result)

        response = {
            "id": "modr-" + str(request.state.start_time),
            "model": "text-moderation-latest",
            "results": results,
            "usage": {
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens
            }
        }

        return JSONResponse(content=response)

    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text for content moderation.
        
        In production, this would use more sophisticated models.
        For demonstration, we use simple regex patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        # Initialize scores and flags
        category_scores = {}
        flagged = False
        
        # Check each category
        for category, pattern in self.patterns.items():
            # Count matches and normalize score
            matches = len(re.findall(pattern, text.lower()))
            score = min(1.0, matches * 0.3)  # Simple scoring
            category_scores[category] = score
            
            # Update flagged status
            if score > self.score_thresholds[category]:
                flagged = True

        return {
            "flagged": flagged,
            "categories": {
                category: score > self.score_thresholds[category]
                for category, score in category_scores.items()
            },
            "category_scores": category_scores
        }

    async def validate_request(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate moderations request.
        
        Args:
            data: Request data
            
        Returns:
            Dict[str, str]: Error message if validation fails, empty dict if successful
        """
        if "input" not in data:
            return {"error": "input is required"}

        input_data = data["input"]
        if not isinstance(input_data, (str, list)):
            return {"error": "input must be a string or array of strings"}

        if isinstance(input_data, list):
            if not input_data:
                return {"error": "input array must not be empty"}
            if not all(isinstance(item, str) for item in input_data):
                return {"error": "all input items must be strings"}
            if len(input_data) > 100:  # OpenAI's limit
                return {"error": "maximum of 100 items allowed for moderation"}

        if isinstance(input_data, str) and not input_data:
            return {"error": "input string must not be empty"}

        return {}

    def _get_model_info(self) -> Dict[str, Any]:
        """Get information about the moderation model.
        
        Returns:
            Dict[str, Any]: Model information
        """
        return {
            "id": "text-moderation-latest",
            "ready": True,
            "status": {
                "ready": True,
                "status": "operational",
                "error": None
            }
        }
