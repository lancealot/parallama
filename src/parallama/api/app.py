from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..gateway.router import router as gateway_router
from ..gateway import GatewayRegistry
from ..gateway.ollama import OllamaGateway
from ..gateway.openai import OpenAIGateway
from ..core.config import Settings

app = FastAPI(
    title="Parallama",
    description="Multi-user authentication and access management service for Ollama",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings
settings = Settings()

# Register gateways
GatewayRegistry.register("ollama", OllamaGateway(settings.ollama))
GatewayRegistry.register("openai", OpenAIGateway(settings.openai))

# Include gateway router
app.include_router(gateway_router)

# Root endpoint for API discovery
@app.get("/")
async def root():
    """API discovery endpoint."""
    return {
        "name": "Parallama API Gateway",
        "version": "1.0.0",
        "gateways": {
            "ollama": {
                "base_path": "/ollama/v1",
                "status": "active",
                "features": ["text generation", "chat completion", "model management"]
            },
            "openai": {
                "base_path": "/openai/v1",
                "status": "active",
                "features": ["text completion", "chat completion"],
                "model_mappings": {
                    "gpt-3.5-turbo": "llama2",
                    "gpt-4": "llama2:70b"
                }
            }
        }
    }
