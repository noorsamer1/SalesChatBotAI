from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import openai_routes
from app.routes import auth_routes    # <-- NEW: Auth endpoints
from app.routes import chat_routes    # <-- NEW: Chat endpoints
from app.routes import analytics_routes  # <-- NEW: Analytics endpoints

app = FastAPI()

# Allow frontend (Vite on port 5174) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174","http://localhost:5173","http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(chat_routes.router, prefix="/chat", tags=["chat"])
app.include_router(analytics_routes.analytics_routes)  # Analytics dashboard
app.include_router(openai_routes.router)  # (Optional: keep for direct model endpoint)

# Optional: Root path
@app.get("/")
def root():
    return {"message": "LLM Chatbot Backend Status: Nominal"}
