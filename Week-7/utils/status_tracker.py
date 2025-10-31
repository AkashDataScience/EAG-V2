import time
from typing import Dict, Optional
import uuid
from threading import Lock
import sys
import os
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import IndexingStatus

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("yt_rag.status_tracker")

class StatusTracker:
    def __init__(self):
        self.operations: Dict[str, Dict] = {}
        self._lock = Lock()
    
    def create_operation(self, video_url: str) -> str:
        """Create a new indexing operation and return its ID."""
        operation_id = str(uuid.uuid4())
        with self._lock:
            self.operations[operation_id] = {
                "status": IndexingStatus.PENDING.value,  # Store as string
                "video_url": video_url,
                "start_time": time.time(),
                "current_time": time.time(),
                "message": "Operation created",
                "error": None
            }
        return operation_id
    
    def update_status(self, operation_id: str, status: IndexingStatus, message: str = "", error: Optional[str] = None):
        """Update the status of an operation."""
        if operation_id not in self.operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        with self._lock:
            self.operations[operation_id].update({
                "status": status.value,  # Store as string
                "current_time": time.time(),
                "message": message,
                "error": error
            })
            logger.info(f"Status updated: {operation_id} -> {status.value}: {message}")
    
    def get_status(self, operation_id: str) -> Dict:
        """Get the current status of an operation."""
        if operation_id not in self.operations:
            raise ValueError(f"Operation {operation_id} not found")
        
        with self._lock:
            status_data = self.operations[operation_id].copy()
            # Calculate elapsed time using current time instead of stored current_time
            elapsed = time.time() - status_data["start_time"]
            status_data["elapsed_seconds"] = round(elapsed, 1)
            return status_data
    
    def cleanup_old_operations(self, max_age_hours: int = 24):
        """Clean up operations older than max_age_hours."""
        current_time = time.time()
        with self._lock:
            to_remove = []
            for op_id, op_data in self.operations.items():
                if current_time - op_data["start_time"] > max_age_hours * 3600:
                    to_remove.append(op_id)
            
            for op_id in to_remove:
                del self.operations[op_id]
            
            logger.info(f"Cleaned up {len(to_remove)} old operations") 