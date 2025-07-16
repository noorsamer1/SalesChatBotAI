from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
from app.routes import openai_routes  # import router

app = FastAPI()

# Allow frontend (Vite on port 5173) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
=======
from app.routes import openai_routes
from app.routes import auth_routes    # <-- NEW: Auth endpoints
from app.routes import chat_routes    # <-- NEW: Chat endpoints

app = FastAPI()

# Allow frontend (Vite on port 5174) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
>>>>>>> master
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD

# Register API routes
app.include_router(openai_routes.router)
=======
# Register API routes
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(chat_routes.router, prefix="/chat", tags=["chat"])
app.include_router(openai_routes.router)  # (Optional: keep for direct model endpoint)
>>>>>>> master

# Optional: Root path
@app.get("/")
def root():
    return {"message": "LLM Chatbot Backend Status: Nominal"}
