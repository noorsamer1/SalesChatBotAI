from fastapi import FastAPI
from app.routes import openai_routes  # import your router

app = FastAPI()

# Register API routes
app.include_router(openai_routes.router)

# Optional: Root path
@app.get("/")
def root():
    return {"message": "LLM Chatbot Backend Status: Nominal"}
