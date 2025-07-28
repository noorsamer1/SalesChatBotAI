from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import openai_routes
from app.routes import auth_routes    # <-- NEW: Auth endpoints
from app.routes import chat_routes    # <-- NEW: Chat endpoints
from app.routes import analytics_routes  # <-- NEW: Analytics endpoints

app = FastAPI()

# Allow frontend to access backend - Updated for server deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:5173", 
        "http://localhost:3000",
        "http://localhost:8501",  # New frontend port
        "http://194.165.140.77:8501",  # External frontend URL
        "http://194.165.140.77:5173",  # Backup external URL
        "https://194.165.140.77:8501",  # HTTPS frontend URL
        "https://194.165.140.77:5173",  # HTTPS backup URL
        "http://172.24.225.99:8501",  # Local machine frontend
    ],
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

# Server startup configuration
if __name__ == "__main__":
    import uvicorn
    
    # HTTPS Configuration - Use same certificates as nginx
    ssl_keyfile = "/etc/ssl/private/ssl-cert-snakeoil.key"
    ssl_certfile = "/etc/ssl/certs/ssl-cert-snakeoil.pem"
    
    try:
        # Try HTTPS first
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8502,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    except Exception as e:
        print(f"HTTPS failed: {e}")
        print("Falling back to HTTP...")
        # Fallback to HTTP if SSL fails
        uvicorn.run(app, host="0.0.0.0", port=8502)
