from fastapi import APIRouter, HTTPException
from app.models.question import Question
from app.services.openai_service import get_openai_response

router = APIRouter()

@router.post("/ask")
async def ask_openai(question: Question):
    try:
        result = get_openai_response(question.prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
