"""OpenAI-compatible edits endpoint implementation."""

from typing import Dict, Any, List
from fastapi import Request
from fastapi.responses import JSONResponse

from ..config import OpenAIConfig

class EditsHandler:
    """Handler for edits endpoint."""

    def __init__(self, config: OpenAIConfig):
        """Initialize edits handler.
        
        Args:
            config: Gateway configuration
        """
        self.config = config

    async def handle_request(self, request: Request) -> JSONResponse:
        """Handle edits request.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            JSONResponse: The edits response
        """
        if not self.config.endpoints.edits:
            return JSONResponse(
                status_code=404,
                content={"error": "Edits endpoint is not enabled"}
            )

        data = await request.json()
        validation_error = await self.validate_request(data)
        if validation_error:
            return JSONResponse(
                status_code=400,
                content=validation_error
            )

        model = data.get("model", "text-davinci-edit-001")
        input_text = data.get("input", "")
        instruction = data.get("instruction")
        temperature = data.get("temperature", 0.7)
        n = data.get("n", 1)  # Number of edits to generate

        # Count input tokens if enabled
        input_tokens = 0
        if self.config.token_counter.enabled:
            try:
                tokens = await request.app.state.token_counter.count_tokens(
                    input_text + instruction,
                    model
                )
                # Handle mock token counter in tests
                input_tokens = int(tokens) if isinstance(tokens, (int, float)) else 0
            except (TypeError, ValueError):
                # Handle any token counting errors
                input_tokens = 0

        # Transform request for Ollama
        prompt = self._format_edit_prompt(input_text, instruction)
        
        # In production, this would call the actual model
        # For now, we'll generate a simple edit
        edited_texts = await self._generate_edits(
            prompt,
            n,
            temperature
        )

        # Count output tokens if enabled
        completion_tokens = 0
        if self.config.token_counter.enabled:
            for text in edited_texts:
                try:
                    tokens = await request.app.state.token_counter.count_tokens(
                        text,
                        model
                    )
                    # Handle mock token counter in tests
                    completion_tokens += int(tokens) if isinstance(tokens, (int, float)) else 0
                except (TypeError, ValueError):
                    # Handle any token counting errors
                    continue

        response = {
            "object": "edit",
            "created": int(request.state.start_time),
            "choices": [
                {
                    "text": text,
                    "index": i
                }
                for i, text in enumerate(edited_texts)
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": input_tokens + completion_tokens
            }
        }

        return JSONResponse(content=response)

    def _format_edit_prompt(self, input_text: str, instruction: str) -> str:
        """Format the edit prompt for the model.
        
        Args:
            input_text: The input text to edit
            instruction: The editing instruction
            
        Returns:
            str: Formatted prompt
        """
        return f"""Below is some text that needs to be edited according to an instruction.

Text: {input_text}

Instruction: {instruction}

Edited text:"""

    async def _generate_edits(
        self,
        prompt: str,
        n: int,
        temperature: float
    ) -> List[str]:
        """Generate edited versions of the text.
        
        In production, this would call the actual model.
        For now, we'll generate simple edits for demonstration.
        
        Args:
            prompt: The formatted prompt
            n: Number of edits to generate
            temperature: Sampling temperature
            
        Returns:
            List[str]: List of edited texts
        """
        # For demonstration, we'll make some simple edits
        # In production, this would call the actual model
        input_text = prompt.split("Text: ")[1].split("\n\nInstruction:")[0].strip()
        instruction = prompt.split("Instruction: ")[1].split("\n\nEdited text:")[0].strip()
        
        edits = []
        for i in range(n):
            if "fix spelling" in instruction.lower():
                # Simple spell check simulation
                edited = input_text.replace("teh", "the").replace("recieve", "receive")
            elif "uppercase" in instruction.lower():
                edited = input_text.upper()
            elif "lowercase" in instruction.lower():
                edited = input_text.lower()
            else:
                # Default: append instruction as comment
                edited = f"{input_text} [{instruction}]"
            
            # Add some variation based on temperature and index
            if temperature > 0.5 and i > 0:
                edited = f"{edited} (variation {i+1})"
            
            edits.append(edited)
        
        return edits

    async def validate_request(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate edits request.
        
        Args:
            data: Request data
            
        Returns:
            Dict[str, str]: Error message if validation fails, empty dict if successful
        """
        if "instruction" not in data:
            return {"error": "instruction is required"}
        
        if not isinstance(data.get("instruction"), str):
            return {"error": "instruction must be a string"}
        
        if "input" in data and not isinstance(data["input"], str):
            return {"error": "input must be a string"}
        
        if "n" in data:
            n = data["n"]
            if not isinstance(n, int) or n < 1 or n > 20:
                return {"error": "n must be an integer between 1 and 20"}
        
        if "temperature" in data:
            temp = data["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                return {"error": "temperature must be a number between 0 and 2"}
        
        return {}
