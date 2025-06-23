from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import openai_routes  # import router

app = FastAPI()

# Allow frontend (Vite on port 5173) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routes
app.include_router(openai_routes.router)

# Optional: Root path
@app.get("/")
def root():
    return {"message": "LLM Chatbot Backend Status: Nominal"}
