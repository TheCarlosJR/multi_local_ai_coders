"""
PHASE 9: Chat Interface for Continue.dev Integration

Dual-mode support for:
1. Batch execution (existing): python main.py "goal"
2. Chat interface (new): HTTP API for Continue.dev IDE plugin

Allows running agent as interactive service while keeping batch mode.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import json
import asyncio
from enum import Enum

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from core.agent_runner import AgentRunner
from core.config import PROJECT_ROOT


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat API request."""
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict] = None


class ChatResponse(BaseModel):
    """Chat API response."""
    session_id: str
    message: str
    status: str  # "thinking", "executing", "completed", "error"
    result: Optional[Dict] = None
    error: Optional[str] = None
    timestamp: str


class SessionMode(str, Enum):
    """Session execution mode."""
    BATCH = "batch"  # Single execution
    INTERACTIVE = "interactive"  # Multi-turn chat


class AgentSession:
    """Manages a chat session with the agent."""
    
    def __init__(self, session_id: str, mode: SessionMode = SessionMode.INTERACTIVE):
        self.session_id = session_id
        self.mode = mode
        self.messages: List[ChatMessage] = []
        self.created_at = datetime.now()
        self.runner = AgentRunner()
        self.current_execution = None
        self.execution_history = []
    
    def add_message(self, role: str, content: str) -> ChatMessage:
        """Add message to conversation history."""
        msg = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        self.messages.append(msg)
        return msg
    
    async def execute_goal(self, goal: str) -> Dict[str, Any]:
        """
        Execute a goal and return result.
        
        Args:
            goal: Task/objective for the agent
        
        Returns:
            Execution result with status and output
        """
        try:
            # Record in conversation
            self.add_message("user", goal)
            
            # Run agent
            result = await asyncio.to_thread(self.runner.run, goal)
            
            # Record execution
            self.execution_history.append({
                "goal": goal,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Extract result message
            result_msg = self._format_result(result)
            self.add_message("assistant", result_msg)
            
            return {
                "success": True,
                "result": result,
                "message": result_msg
            }
        
        except Exception as e:
            error_msg = f"Error executing goal: {str(e)}"
            self.add_message("assistant", error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    
    def _format_result(self, result: Dict) -> str:
        """Format execution result as readable message."""
        if isinstance(result, dict):
            success = result.get("success", False)
            goal = result.get("goal", "Task")
            output = result.get("result", result.get("message", "Completed"))
            
            if success:
                return f"✓ {goal}\n\n**Result**: {output}"
            else:
                return f"✗ {goal}\n\n**Error**: {output}"
        
        return str(result)
    
    def get_history(self) -> List[ChatMessage]:
        """Get conversation history."""
        return self.messages
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "mode": self.mode.value,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.messages),
            "execution_count": len(self.execution_history),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp
                }
                for msg in self.messages
            ]
        }


class ChatInterface:
    """
    Manages chat sessions and integrates with agent runner.
    
    Provides both:
    - HTTP API for Continue.dev
    - Programmatic interface for direct use
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.sessions: Dict[str, AgentSession] = {}
        self.session_counter = 0
        
        # Initialize FastAPI if available
        self.app = None
        if FASTAPI_AVAILABLE:
            self._setup_fastapi()
    
    def _setup_fastapi(self):
        """Setup FastAPI application with routes."""
        self.app = FastAPI(
            title="AI Agent Chat Interface",
            description="Chat API for AI Agent integration with Continue.dev",
            version="1.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Define routes
        @self.app.post("/api/chat", response_model=ChatResponse)
        async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
            """Chat endpoint for Continue.dev integration."""
            return await self.handle_chat(
                request.message,
                request.session_id,
                background_tasks
            )
        
        @self.app.get("/api/status")
        async def status_endpoint():
            """Get agent status."""
            return {
                "status": "operational",
                "sessions_active": len(self.sessions),
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.post("/api/session/new")
        async def new_session_endpoint():
            """Create new chat session."""
            session_id = self._create_session()
            return {
                "session_id": session_id,
                "created_at": datetime.now().isoformat()
            }
        
        @self.app.get("/api/session/{session_id}")
        async def get_session_endpoint(session_id: str):
            """Get session details and history."""
            session = self.sessions.get(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return session.to_dict()
        
        @self.app.get("/api/session/{session_id}/history")
        async def get_history_endpoint(session_id: str):
            """Get conversation history."""
            session = self.sessions.get(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return {
                "session_id": session_id,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    }
                    for msg in session.get_history()
                ]
            }
        
        @self.app.delete("/api/session/{session_id}")
        async def delete_session_endpoint(session_id: str):
            """End a session."""
            if session_id in self.sessions:
                del self.sessions[session_id]
                return {"status": "deleted", "session_id": session_id}
            raise HTTPException(status_code=404, detail="Session not found")
    
    async def handle_chat(self, message: str, session_id: Optional[str],
                         background_tasks: Optional[BackgroundTasks] = None) -> ChatResponse:
        """
        Handle incoming chat message.
        
        Args:
            message: User message
            session_id: Session ID (creates new if None)
            background_tasks: FastAPI BackgroundTasks
        
        Returns:
            ChatResponse with execution result
        """
        # Create or get session
        if not session_id:
            session_id = self._create_session()
        elif session_id not in self.sessions:
            self.sessions[session_id] = AgentSession(session_id)
        
        session = self.sessions[session_id]
        
        try:
            # Execute goal
            result = await session.execute_goal(message)
            
            return ChatResponse(
                session_id=session_id,
                message=result["message"],
                status="completed" if result["success"] else "error",
                result=result.get("result"),
                error=result.get("error"),
                timestamp=datetime.now().isoformat()
            )
        
        except Exception as e:
            return ChatResponse(
                session_id=session_id,
                message=f"Error: {str(e)}",
                status="error",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )
    
    def _create_session(self) -> str:
        """Create new session and return session ID."""
        self.session_counter += 1
        session_id = f"session_{self.session_counter}_{datetime.now().timestamp()}"
        self.sessions[session_id] = AgentSession(session_id)
        return session_id
    
    def run_server(self, debug: bool = False):
        """
        Start HTTP server for Continue.dev integration.
        
        Args:
            debug: Enable debug mode
        """
        if not FASTAPI_AVAILABLE:
            print("❌ FastAPI not installed. Install with:")
            print("   pip install fastapi uvicorn")
            return
        
        print(f"🚀 Starting Chat Interface at http://{self.host}:{self.port}")
        print(f"📚 API Docs at http://{self.host}:{self.port}/docs")
        print(f"🔌 Continue.dev Integration: ws://{self.host}:{self.port}/api/chat")
        
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            reload=debug,
            log_level="info" if debug else "error"
        )
    
    def save_session(self, session_id: str, filepath: Optional[str] = None) -> str:
        """
        Save session to file for persistence.
        
        Args:
            session_id: Session to save
            filepath: Output file (default: sessions/{session_id}.json)
        
        Returns:
            Path to saved file
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if not filepath:
            Path("sessions").mkdir(exist_ok=True)
            filepath = f"sessions/{session_id}.json"
        
        with open(filepath, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
        
        return filepath
    
    def load_session(self, filepath: str) -> str:
        """
        Load session from file.
        
        Args:
            filepath: Path to session file
        
        Returns:
            Session ID
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        session_id = data["session_id"]
        session = AgentSession(session_id, SessionMode(data["mode"]))
        
        # Restore messages
        for msg_data in data.get("messages", []):
            session.add_message(msg_data["role"], msg_data["content"])
        
        self.sessions[session_id] = session
        return session_id


# Convenience functions for batch mode (existing functionality)

def run_batch(goal: str) -> Dict[str, Any]:
    """
    Run agent in batch mode (existing single-execution mode).
    
    Args:
        goal: Task to execute
    
    Returns:
        Execution result
    """
    runner = AgentRunner()
    return runner.run(goal)


def run_interactive(host: str = "127.0.0.1", port: int = 8000):
    """
    Run agent in interactive mode (new HTTP API).
    
    Args:
        host: Server host
        port: Server port
    """
    interface = ChatInterface(host, port)
    interface.run_server()


# Export for use
__all__ = [
    "ChatInterface",
    "AgentSession",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "run_batch",
    "run_interactive"
]
