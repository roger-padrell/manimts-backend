from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import os
import tempfile
import uuid
import asyncio
from enum import Enum
from typing import Dict, Optional
from datetime import datetime
import psutil
import platform
import shutil

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create media directory if it doesn't exist
MEDIA_DIR = os.path.join(os.getcwd(), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# Mount the media directory
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

class ExecutionStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

class ExecutionResponse(BaseModel):
    execution_id: str

class StatusResponse(BaseModel):
    status: ExecutionStatus
    error_message: Optional[str] = None
    video_url: Optional[str] = None

class ResultResponse(BaseModel):
    stdout: str
    stderr: str
    return_code: int
    video_url: str

# In-memory storage for executions
executions: Dict[str, dict] = {}

# Start time of the server
START_TIME = datetime.now()

@app.get("/")
async def root():
    return {"name": "manimts-backend"}

@app.get("/health")
async def health_check():
    # Count running tasks
    running_tasks = sum(1 for execution in executions.values() 
                       if execution["status"] == ExecutionStatus.RUNNING)
    
    # Get system information
    process = psutil.Process()
    memory_info = process.memory_info()
    
    return {
        "status": "healthy",
        "uptime_seconds": (datetime.now() - START_TIME).total_seconds(),
        "running_tasks": running_tasks,
        "total_tasks_handled": len(executions),
        "system_info": {
            "cpu_percent": process.cpu_percent(),
            "memory_usage_mb": memory_info.rss / 1024 / 1024,  # Convert to MB
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "execution_stats": {
            "success": sum(1 for e in executions.values() if e["status"] == ExecutionStatus.SUCCESS),
            "error": sum(1 for e in executions.values() if e["status"] == ExecutionStatus.ERROR),
            "running": running_tasks
        }
    }

async def execute_code_task(execution_id: str, code: str):
    try:
        # Create a temporary file with the provided code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name
            # Get base name without extension
            base_name = os.path.splitext(os.path.basename(temp_path))[0]

        try:
            # Execute manim command
            command = f"manim render {temp_path} MainScene --media_dir {MEDIA_DIR}"
            command_parts = command.split()
            
            # Execute the code with the provided command
            process = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
                # The video will be in ./media/videos/{base_name}/1080p60/MainScene.mp4
                video_path = os.path.join("videos", base_name, "1080p60", "MainScene.mp4")
                
                result = {
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "return_code": process.returncode,
                    "video_url": f"http://manimts-backend.onrender.com/media/{video_path}"
                }
                executions[execution_id]["status"] = ExecutionStatus.SUCCESS
                executions[execution_id]["result"] = result
            except asyncio.TimeoutError:
                if process.returncode is None:
                    process.terminate()
                    await process.wait()
                executions[execution_id]["status"] = ExecutionStatus.ERROR
                executions[execution_id]["error_message"] = "Execution timed out after 300 seconds"

        finally:
            # Clean up the temporary file
            os.unlink(temp_path)

    except Exception as e:
        executions[execution_id]["status"] = ExecutionStatus.ERROR
        executions[execution_id]["error_message"] = str(e)

@app.post("/execute", response_model=ExecutionResponse)
async def start_execution(request: Request):
    # Get raw text from request body
    code = await request.body()
    code = code.decode()
    
    execution_id = str(uuid.uuid4())
    executions[execution_id] = {
        "status": ExecutionStatus.RUNNING,
        "result": None,
        "error_message": None
    }
    
    # Start the execution task in the background
    asyncio.create_task(execute_code_task(execution_id, code))
    
    return ExecutionResponse(execution_id=execution_id)

@app.get("/status/{execution_id}", response_model=StatusResponse)
async def get_status(execution_id: str):
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = executions[execution_id]
    video_url = None
    if execution["status"] == ExecutionStatus.SUCCESS and execution["result"]:
        video_url = execution["result"]["video_url"]
    
    return StatusResponse(
        status=execution["status"],
        error_message=execution["error_message"],
        video_url=video_url
    )

@app.get("/response/{execution_id}", response_model=ResultResponse)
async def get_response(execution_id: str):
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = executions[execution_id]
    if execution["status"] != ExecutionStatus.SUCCESS:
        raise HTTPException(
            status_code=400, 
            detail=f"Execution is not completed successfully. Current status: {execution['status']}"
        )
    
    return ResultResponse(**execution["result"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
