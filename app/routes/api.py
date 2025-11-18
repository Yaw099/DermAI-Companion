from flask import Blueprint, request, jsonify, session
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, List
from app.services.ai_client import ask_ai
from app.services.red_flags import check_red_flags
import re

api_bp = Blueprint('api', __name__)

class Message(BaseModel):
    """Individual message in conversation"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=5000)

class ChatRequest(BaseModel):
    """Request for AI chat endpoint"""
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="User's question about dermatology"
    )
    conversation: List[Message] = Field(
        default_factory=list,
        max_length=50,
        description="Previous conversation history"
    )
    
    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """Remove potentially harmful characters"""
        #get rid of HTML tags
        v = re.sub(r'<[^>]+>', '', v)
        #get rid of extra whitespace
        return v.strip()

class JournalEntryRequest(BaseModel):
    """Request for creating journal entry"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    symptoms: List[str] = Field(default_factory=list, max_length=20)
    severity: Optional[int] = Field(None, ge=1, le=10)
    photo_urls: List[str] = Field(default_factory=list, max_length=5)
    
    @field_validator('symptoms')
    @classmethod
    def validate_symptoms(cls, v: List[str]) -> List[str]:
        """Ensure each symptom is reasonable length"""
        return [s.strip() for s in v if s.strip() and len(s.strip()) <= 100]

class RedFlagCheckRequest(BaseModel):
    """Request to check for medical red flags"""
    text: str = Field(..., min_length=1, max_length=2000)

class ExplainRequest(BaseModel):
    """Request to explain medical terms"""
    term: str = Field(..., min_length=1, max_length=200)
    context: Optional[str] = Field(None, max_length=1000)


@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    AI chat endpoint with PubMed RAG
    
    Request body:
    {
        "message": "What causes eczema?",
        "conversation": [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
    }
    """
    try:
        #Validate request
        data = ChatRequest(**request.json)
        
        #Check for red flags in user's message
        red_flags = check_red_flags(data.message)
        
        #Start Building conversation history
        conversation = [
            {"role": msg.role, "content": msg.content} 
            for msg in data.conversation
        ]
        conversation.append({
            "role": "user", 
            "content": data.message
        })
        
        #Get AI response with PubMed RAG
        ai_response = ask_ai(conversation)
        
        return jsonify({
            "success": True,
            "response": ai_response,
            "red_flags": red_flags,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Add real timestamp
        }), 200
    
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": "Invalid request data",
            "details": e.errors()
        }), 400
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@api_bp.route('/journal', methods=['POST'])
def create_journal_entry():
    """
    Create a journal entry
    
    Request body:
    {
        "title": "Red rash on arm",
        "content": "Started noticing a red rash...",
        "symptoms": ["redness", "itching"],
        "severity": 5,
        "photo_urls": ["https://..."]
    }
    """
    try: 
        return jsonify({
            "success": True,
            "message": "Journal entry created",
            "entry_id": "temp_123",  # TODO: Return actual ID
            "data": data.model_dump()
        }), 201
    
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": "Invalid request data",
            "details": e.errors()
        }), 400
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@api_bp.route('/red-flags', methods=['POST'])
def check_red_flags_endpoint():
    """
    Check text for medical red flags
    
    Request body:
    {
        "text": "I have severe chest pain and difficulty breathing"
    }
    """
    try:
        #Validate request
        data = RedFlagCheckRequest(**request.json)
        
        #check for red flags
        flags = check_red_flags(data.text)
        
        return jsonify({
            "success": True,
            "red_flags": flags,
            "urgent": len(flags) > 0
        }), 200
    
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": "Invalid request data",
            "details": e.errors()
        }), 400


@api_bp.route('/explain', methods=['POST'])
def explain_term():
    """
    Explain medical terminology in plain language
    
    Request body:
    {
        "term": "melanoma",
        "context": "My doctor mentioned this"
    }
    """
    try:
        #Validate request
        data = ExplainRequest(**request.json)
        
        #Build conversation for AI
        prompt = f"Explain the medical term '{data.term}' in simple language."
        if data.context:
            prompt += f" Context: {data.context}"
        
        conversation = [{"role": "user", "content": prompt}]
        explanation = ask_ai(conversation)
        
        return jsonify({
            "success": True,
            "term": data.term,
            "explanation": explanation
        }), 200
    
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": "Invalid request data",
            "details": e.errors()
        }), 400
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "dermatology-api",
        "version": "1.0.0"
    }), 200


@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@api_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "error": "Method not allowed"
    }), 405

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500