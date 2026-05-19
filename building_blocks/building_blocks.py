# =============================================================================
# Systems Thinking in the AI Era
# https://systemthinkinglab.ai
#
# This code is part of the "Systems Thinking in the AI Era" course series.
# For more information, educational content, and courses, visit:
# https://systemthinkinglab.ai
# =============================================================================

"""
Systems Thinking in the AI Era I: Universal Building Blocks
Educational implementations of the 7 building blocks for pattern learning

These classes focus on:
- Clear interfaces that demonstrate building block capabilities
- Simple implementations that highlight core concepts
- Composability for creating common architectural patterns
- Educational value over production optimization
- Developing system thinking skills that complement AI capabilities
"""

import time
import threading
import json
import sqlite3
import numpy as np
from typing import Any, Dict, List, Optional, Callable
from queue import Queue as ThreadQueue
from dataclasses import dataclass
from datetime import datetime, timedelta


# =============================================================================
# TASK BUILDING BLOCKS (Blue)
# =============================================================================

class Service:
    """
    Service Building Block - Request/Response Processing
    
    Handles synchronous requests with immediate responses.
    Good for: API endpoints, user-facing operations, fast processing
    """
    
    def __init__(self, name: str):
        self.name = name
        self.routes = {}
        self.request_count = 0
        self.response_times = []
    
    def route(self, path: str):
        """Decorator to register request handlers"""
        def decorator(handler_func):
            self.routes[path] = handler_func
            return handler_func
        return decorator
    
    def handle_request(self, path: str, data: Dict = None) -> Dict:
        """Process a request and return response"""
        start_time = time.time()
        self.request_count += 1
        
        if path not in self.routes:
            return {"error": "Route not found", "status": 404}
        
        try:
            # Execute the request handler
            handler = self.routes[path]
            if data:
                response = handler(data)
            else:
                response = handler()
            
            # Track performance
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            
            return {"data": response, "status": 200, "response_time": response_time}
            
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    def get_stats(self) -> Dict:
        """Get service performance statistics"""
        if not self.response_times:
            return {"requests": 0, "avg_response_time": 0}
        
        return {
            "requests": self.request_count,
            "avg_response_time": sum(self.response_times) / len(self.response_times),
            "max_response_time": max(self.response_times)
        }


class Worker:
    """
    Worker Building Block - Background Processing
    
    Handles long-running tasks asynchronously without blocking.
    Good for: Background jobs, data processing, scheduled tasks
    """
    
    def __init__(self, name: str, max_concurrent_jobs: int = 3):
        self.name = name
        self.max_concurrent_jobs = max_concurrent_jobs
        self.job_handlers = {}
        self.active_jobs = {}
        self.completed_jobs = []
        self.failed_jobs = []
        self.running = False
        self.worker_thread = None
    
    def register_job_type(self, job_type: str, handler: Callable):
        """Register a handler for a specific job type"""
        self.job_handlers[job_type] = handler
    
    def submit_job(self, job_type: str, job_data: Dict, job_id: str = None) -> str:
        """Submit a job for background processing"""
        if job_id is None:
            import random
            job_id = f"{job_type}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        job = {
            "id": job_id,
            "type": job_type,
            "data": job_data,
            "submitted_at": datetime.now(),
            "status": "queued"
        }
        
        # In a real implementation, this would go to a proper queue
        # For education, we'll use a simple dict
        self.active_jobs[job_id] = job
        return job_id
    
    def start(self):
        """Start the worker thread for background processing"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._work_loop, daemon=True)
            self.worker_thread.start()
            print(f"🔧 Worker '{self.name}' started")
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)  # Wait up to 5 seconds for clean shutdown
    
    def _work_loop(self):
        """Main worker loop - processes jobs from the queue"""
        while self.running:
            # Find queued jobs
            queued_jobs = [job for job in self.active_jobs.values() 
                          if job["status"] == "queued"]
            
            # Process jobs up to max concurrent limit
            processing_count = len([job for job in self.active_jobs.values() 
                                  if job["status"] == "processing"])
            
            for job in queued_jobs:
                if processing_count >= self.max_concurrent_jobs:
                    break
                
                # Start processing job
                job["status"] = "processing"
                job["started_at"] = datetime.now()
                threading.Thread(target=self._process_job, args=(job,)).start()
                processing_count += 1
            
            time.sleep(0.1)  # Small delay to prevent busy waiting
    
    def _process_job(self, job: Dict):
        """Process a single job"""
        try:
            job_type = job["type"]
            if job_type not in self.job_handlers:
                raise Exception(f"No handler for job type: {job_type}")
            
            # Execute the job handler
            handler = self.job_handlers[job_type]
            result = handler(job["data"])
            
            # Mark job as completed
            job["status"] = "completed"
            job["completed_at"] = datetime.now()
            job["result"] = result
            
            # Move to completed jobs
            self.completed_jobs.append(job)
            del self.active_jobs[job["id"]]
            
        except Exception as e:
            # Mark job as failed
            job["status"] = "failed"
            job["error"] = str(e)
            job["failed_at"] = datetime.now()
            
            # Move to failed jobs
            self.failed_jobs.append(job)
            del self.active_jobs[job["id"]]
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get the status of a specific job"""
        # Check active jobs
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        
        # Check completed jobs
        for job in self.completed_jobs:
            if job["id"] == job_id:
                return job
        
        # Check failed jobs
        for job in self.failed_jobs:
            if job["id"] == job_id:
                return job
        
        return None
    
    def get_stats(self):
        """Get worker performance statistics"""
        total_jobs = len(self.active_jobs) + len(self.completed_jobs) + len(self.failed_jobs)
        return {
            "total_jobs": total_jobs,
            "completed_jobs": len(self.completed_jobs),
            "failed_jobs": len(self.failed_jobs),
            "active_jobs": len(self.active_jobs),
            "success_rate": len(self.completed_jobs) / max(1, len(self.completed_jobs) + len(self.failed_jobs)) * 100
        }


# =============================================================================
# STORAGE BUILDING BLOCKS (Red)
# =============================================================================

class KeyValueStore:
    """
    Key Value Store Building Block - Fast Dictionary Lookups
    
    Stores data as key-value pairs for fast retrieval.
    Good for: Caching, session management, configuration, counters
    """
    
    def __init__(self, name: str, max_size: int = 1000):
        self.name = name
        self.max_size = max_size
        self.data = {}
        self.expiry_times = {}
        self.access_count = 0
        self.hit_count = 0
        self.lock = threading.Lock()
    
    def set(self, key: str, value: Any, ttl_seconds: int = None) -> bool:
        """Set a key-value pair with optional TTL"""
        with self.lock:
            # Check if we need to evict items
            if len(self.data) >= self.max_size and key not in self.data:
                self._evict_oldest()
            
            self.data[key] = value
            
            # Set expiry time if TTL provided
            if ttl_seconds:
                self.expiry_times[key] = datetime.now() + timedelta(seconds=ttl_seconds)
            elif key in self.expiry_times:
                del self.expiry_times[key]
            
            return True
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        with self.lock:
            self.access_count += 1
            
            # Check if key exists
            if key not in self.data:
                return None
            
            # Check if key has expired
            if key in self.expiry_times:
                if datetime.now() > self.expiry_times[key]:
                    del self.data[key]
                    del self.expiry_times[key]
                    return None
            
            self.hit_count += 1
            return self.data[key]
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair"""
        with self.lock:
            if key in self.data:
                del self.data[key]
                if key in self.expiry_times:
                    del self.expiry_times[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists and hasn't expired"""
        return self.get(key) is not None
    
    def keys(self) -> List[str]:
        """Get all non-expired keys"""
        with self.lock:
            valid_keys = []
            current_time = datetime.now()
            
            for key in list(self.data.keys()):
                if key in self.expiry_times:
                    if current_time > self.expiry_times[key]:
                        del self.data[key]
                        del self.expiry_times[key]
                        continue
                valid_keys.append(key)
            
            return valid_keys
    
    def _evict_oldest(self):
        """Simple eviction strategy - remove first key"""
        if self.data:
            oldest_key = next(iter(self.data))
            del self.data[oldest_key]
            if oldest_key in self.expiry_times:
                del self.expiry_times[oldest_key]
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        hit_rate = (self.hit_count / self.access_count) if self.access_count > 0 else 0
        return {
            "size": len(self.data),
            "access_count": self.access_count,
            "hit_count": self.hit_count,
            "hit_rate": hit_rate,
            "max_size": self.max_size
        }


class FileStore:
    """
    File Store Building Block - Large File Storage
    
    Handles storage and retrieval of files and binary data.
    Good for: Images, videos, documents, backups
    """
    
    def __init__(self, name: str, base_path: str = "./filestore"):
        self.name = name
        self.base_path = base_path
        self.files = {}  # metadata about stored files
        self.total_size = 0
        
        # Create base directory if it doesn't exist
        import os
        os.makedirs(base_path, exist_ok=True)
    
    def store_file(self, file_id: str, content: bytes, metadata: Dict = None) -> bool:
        """Store a file with optional metadata"""
        try:
            file_path = f"{self.base_path}/{file_id}"
            
            # Write file to disk
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Store metadata
            file_info = {
                "id": file_id,
                "size": len(content),
                "stored_at": datetime.now(),
                "path": file_path,
                "metadata": metadata or {}
            }
            
            self.files[file_id] = file_info
            self.total_size += len(content)
            return True
            
        except Exception as e:
            print(f"Error storing file {file_id}: {e}")
            return False
    
    def retrieve_file(self, file_id: str) -> Optional[bytes]:
        """Retrieve file content by ID"""
        if file_id not in self.files:
            return None
        
        try:
            file_path = self.files[file_id]["path"]
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error retrieving file {file_id}: {e}")
            return None
    
    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get file metadata"""
        return self.files.get(file_id)
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file"""
        if file_id not in self.files:
            return False
        
        try:
            import os
            file_path = self.files[file_id]["path"]
            file_size = self.files[file_id]["size"]
            
            os.remove(file_path)
            del self.files[file_id]
            self.total_size -= file_size
            return True
            
        except Exception as e:
            print(f"Error deleting file {file_id}: {e}")
            return False
    
    def list_files(self) -> List[Dict]:
        """List all stored files"""
        return list(self.files.values())
    
    def get_stats(self) -> Dict:
        """Get file store statistics"""
        return {
            "file_count": len(self.files),
            "total_size_bytes": self.total_size,
            "total_size_mb": round(self.total_size / (1024 * 1024), 2)
        }


class Queue:
    """
    Queue Building Block - Ordered Message Processing with Auto-Dispatch
    
    Ensures fair and orderly processing of tasks/messages.
    Automatically dispatches messages to registered subscribers.
    Good for: Event-driven architecture, message passing, workflow coordination
    """
    
    def __init__(self, name: str, max_size: int = 1000):
        self.name = name
        self.max_size = max_size
        self.queue = ThreadQueue(maxsize=max_size)
        self.message_count = 0
        self.processed_count = 0
        self.failed_count = 0
        self.subscribers = {}  # message_type -> callback mapping
        self.running = True
        
        # Start auto-dispatch thread
        self.dispatch_thread = threading.Thread(target=self._auto_dispatch_loop, daemon=True)
        self.dispatch_thread.start()
    
    def subscriber(self, message_type: str = "*"):
        """Decorator to register subscribers that automatically process messages"""
        def decorator(callback_func):
            self.subscribers[message_type] = callback_func
            print(f"📬 Registered auto-subscriber for '{message_type}' in queue '{self.name}'")
            return callback_func
        return decorator
    
    def register_subscriber(self, message_type: str, callback: Callable):
        """Register a subscriber for automatic message processing (alternative to decorator)"""
        self.subscribers[message_type] = callback
        print(f"📬 Registered auto-subscriber for '{message_type}' in queue '{self.name}'")
    
    def enqueue(self, message: Any, message_type: str = "default", priority: int = 0) -> bool:
        """Add a message to the queue - will be auto-dispatched to subscribers"""
        try:
            message_envelope = {
                "id": self.message_count,
                "message": message,
                "message_type": message_type,
                "enqueued_at": datetime.now(),
                "priority": priority
            }
            
            self.queue.put(message_envelope, block=False)
            self.message_count += 1
            print(f"📬 Enqueued {message_type} message to {self.name}")
            return True
            
        except:
            # Queue is full
            print(f"📬 Queue {self.name} is full, message rejected")
            return False
    
    def _auto_dispatch_loop(self):
        """Automatically dequeue messages and dispatch to subscribers"""
        while self.running:
            try:
                # Wait for a message (blocking with timeout)
                message_envelope = self.queue.get(timeout=1.0)
                
                if message_envelope:
                    message_type = message_envelope.get("message_type", "default")
                    message_envelope["dispatched_at"] = datetime.now()
                    
                    # Find the right subscriber
                    callback = None
                    if message_type in self.subscribers:
                        callback = self.subscribers[message_type]
                    elif "*" in self.subscribers:
                        callback = self.subscribers["*"]
                    
                    if callback:
                        try:
                            print(f"📬 Auto-dispatching {message_type} message to subscriber")
                            # Call subscriber with just the message data (cleaner interface)
                            result = callback(message_envelope["message"])
                            self.processed_count += 1
                        except Exception as e:
                            print(f"📬 Error in subscriber for {message_type}: {e}")
                            self.failed_count += 1
                    else:
                        print(f"📬 No subscriber for {message_type} message - dropping")
                        self.failed_count += 1
                        
            except:
                # Timeout or queue empty - continue loop
                continue
    
    def dequeue(self, timeout: float = None) -> Optional[Any]:
        """
        Manual dequeue for cases where auto-dispatch isn't wanted
        Note: Auto-dispatch will handle most messages automatically
        """
        try:
            message_envelope = self.queue.get(timeout=timeout)
            message_envelope["dequeued_at"] = datetime.now()
            return message_envelope
        except:
            return None
    
    def size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()
    
    def is_full(self) -> bool:
        """Check if queue is full"""
        return self.queue.full()
    
    def stop(self):
        """Stop the auto-dispatch thread"""
        self.running = False
        if self.dispatch_thread and self.dispatch_thread.is_alive():
            self.dispatch_thread.join(timeout=2)
    
    def get_stats(self) -> Dict:
        """Get queue statistics"""
        success_rate = (self.processed_count / max(1, self.processed_count + self.failed_count))
        return {
            "current_size": self.size(),
            "max_size": self.max_size,
            "total_enqueued": self.message_count,
            "total_processed": self.processed_count,
            "total_failed": self.failed_count,
            "success_rate": success_rate,
            "active_subscribers": len(self.subscribers),
            "subscriber_types": list(self.subscribers.keys())
        }


class RelationalDB:
    """
    Relational Database Building Block - Structured Data with Relationships
    
    Stores data in tables with relationships and ACID properties.
    Good for: Business data, user accounts, transactions, complex queries
    """
    
    def __init__(self, name: str, db_path: str = ":memory:"):
        self.name = name
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
        self.lock = threading.Lock()
        self.query_count = 0
    
    def create_table(self, table_name: str, schema: str) -> bool:
        """Create a table with the given schema"""
        try:
            with self.lock:
                self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})")
                self.connection.commit()
                return True
        except Exception as e:
            print(f"Error creating table {table_name}: {e}")
            return False
    
    def insert(self, table_name: str, data: Dict) -> Optional[int]:
        """Insert data into a table"""
        try:
            with self.lock:
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = list(data.values())
                
                cursor = self.connection.execute(
                    f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                    values
                )
                self.connection.commit()
                self.query_count += 1
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error inserting into {table_name}: {e}")
            return None
    
    def select(self, table_name: str, where_clause: str = None, params: List = None) -> List[Dict]:
        """Select data from a table"""
        try:
            with self.lock:
                query = f"SELECT * FROM {table_name}"
                if where_clause:
                    query += f" WHERE {where_clause}"
                
                cursor = self.connection.execute(query, params or [])
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                self.query_count += 1
                return results
                
        except Exception as e:
            print(f"Error selecting from {table_name}: {e}")
            return []
    
    def update(self, table_name: str, data: Dict, where_clause: str, params: List = None) -> int:
        """Update data in a table"""
        try:
            with self.lock:
                set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
                values = list(data.values()) + (params or [])
                
                cursor = self.connection.execute(
                    f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}",
                    values
                )
                self.connection.commit()
                self.query_count += 1
                return cursor.rowcount
                
        except Exception as e:
            print(f"Error updating {table_name}: {e}")
            return 0
    
    def delete(self, table_name: str, where_clause: str, params: List = None) -> int:
        """Delete data from a table"""
        try:
            with self.lock:
                cursor = self.connection.execute(
                    f"DELETE FROM {table_name} WHERE {where_clause}",
                    params or []
                )
                self.connection.commit()
                self.query_count += 1
                return cursor.rowcount
                
        except Exception as e:
            print(f"Error deleting from {table_name}: {e}")
            return 0
    
    def execute_transaction(self, operations: List[Callable]) -> bool:
        """Execute multiple operations as a transaction"""
        try:
            with self.lock:
                self.connection.execute("BEGIN TRANSACTION")
                
                for operation in operations:
                    operation()
                
                self.connection.commit()
                return True
                
        except Exception as e:
            self.connection.rollback()
            print(f"Transaction failed: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.lock:
            # Get table count
            cursor = self.connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            )
            table_count = cursor.fetchone()[0]
            
            return {
                "table_count": table_count,
                "query_count": self.query_count
            }


class VectorDB:
    """
    Vector Database Building Block - Similarity-Based Data Retrieval
    
    Stores data as high-dimensional vectors for similarity search.
    Good for: AI embeddings, recommendation systems, semantic search
    """
    
    def __init__(self, name: str, dimension: int = 128):
        self.name = name
        self.dimension = dimension
        self.vectors = {}  # id -> vector mapping
        self.metadata = {}  # id -> metadata mapping
        self.search_count = 0
        self.lock = threading.Lock()
    
    def store_vector(self, vector_id: str, vector: List[float], metadata: Dict = None) -> bool:
        """Store a vector with optional metadata"""
        if len(vector) != self.dimension:
            print(f"Vector dimension mismatch: expected {self.dimension}, got {len(vector)}")
            return False
        
        with self.lock:
            self.vectors[vector_id] = np.array(vector)
            self.metadata[vector_id] = metadata or {}
            return True
    
    def similarity_search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        """Find the most similar vectors"""
        if len(query_vector) != self.dimension:
            print(f"Query vector dimension mismatch: expected {self.dimension}, got {len(query_vector)}")
            return []
        
        with self.lock:
            self.search_count += 1
            query_np = np.array(query_vector)
            similarities = []
            
            for vector_id, vector in self.vectors.items():
                # Calculate cosine similarity
                similarity = np.dot(query_np, vector) / (np.linalg.norm(query_np) * np.linalg.norm(vector))
                similarities.append({
                    "id": vector_id,
                    "similarity": float(similarity),
                    "metadata": self.metadata[vector_id]
                })
            
            # Sort by similarity (descending) and return top_k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:top_k]
    
    def get_vector(self, vector_id: str) -> Optional[List[float]]:
        """Retrieve a vector by ID"""
        with self.lock:
            if vector_id in self.vectors:
                return self.vectors[vector_id].tolist()
            return None
    
    def delete_vector(self, vector_id: str) -> bool:
        """Delete a vector"""
        with self.lock:
            if vector_id in self.vectors:
                del self.vectors[vector_id]
                del self.metadata[vector_id]
                return True
            return False
    
    def list_vectors(self) -> List[str]:
        """List all vector IDs"""
        with self.lock:
            return list(self.vectors.keys())
    
    def get_stats(self) -> Dict:
        """Get vector database statistics"""
        return {
            "vector_count": len(self.vectors),
            "dimension": self.dimension,
            "search_count": self.search_count
        }


# =============================================================================
# EXAMPLE USAGE AND TESTING
# =============================================================================

def demonstrate_building_blocks():
    """
    Example usage showing how building blocks work together
    """
    print("=== Building Block Demonstration ===\n")
    
    # 1. Service Example
    print("1. Service Building Block:")
    api_service = Service("user_api")
    
    @api_service.route("/users")
    def get_users():
        return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    
    response = api_service.handle_request("/users")
    print(f"   Response: {response['data']}")
    print(f"   Stats: {api_service.get_stats()}\n")
    
    # 2. Key Value Store Example
    print("2. Key Value Store Building Block:")
    cache = KeyValueStore("session_cache")
    cache.set("user_123", {"name": "Alice", "role": "admin"}, ttl_seconds=60)
    user_data = cache.get("user_123")
    print(f"   Cached data: {user_data}")
    print(f"   Stats: {cache.get_stats()}\n")
    
    # 3. Queue Example
    print("3. Queue Building Block:")
    task_queue = Queue("email_queue")
    task_queue.enqueue({"to": "user@example.com", "subject": "Welcome"})
    message = task_queue.dequeue()
    print(f"   Dequeued message: {message['message']}")
    print(f"   Stats: {task_queue.get_stats()}\n")
    
    # 4. Relational DB Example
    print("4. Relational Database Building Block:")
    db = RelationalDB("app_db")
    db.create_table("users", "id INTEGER PRIMARY KEY, name TEXT, email TEXT")
    user_id = db.insert("users", {"name": "Alice", "email": "alice@example.com"})
    users = db.select("users", "id = ?", [user_id])
    print(f"   Created user: {users[0]}")
    print(f"   Stats: {db.get_stats()}\n")
    
    # 5. Vector DB Example
    print("5. Vector Database Building Block:")
    vector_db = VectorDB("embeddings", dimension=3)
    vector_db.store_vector("doc1", [1.0, 0.0, 0.0], {"title": "Introduction"})
    vector_db.store_vector("doc2", [0.8, 0.6, 0.0], {"title": "Overview"})
    similar = vector_db.similarity_search([0.9, 0.1, 0.0], top_k=1)
    print(f"   Most similar document: {similar[0]}")
    print(f"   Stats: {vector_db.get_stats()}\n")


if __name__ == "__main__":
    demonstrate_building_blocks()