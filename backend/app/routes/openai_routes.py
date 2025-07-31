from fastapi import APIRouter, HTTPException
from app.schemas.question import Question
from app.services.openai_service import get_openai_response
from app.services.response_parser import parse_reply

router = APIRouter()

@router.post("/ask")
async def ask_openai(question: Question):
    try:
        # Move this get_openai_response(question.prompt) into the parser and then sent the reply from that to here
        response = get_openai_response(question.prompt)
        result = parse_reply(response)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
