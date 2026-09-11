from pydantic import BaseModel


class SpeechTranscriptionResponse(BaseModel):
    text: str
