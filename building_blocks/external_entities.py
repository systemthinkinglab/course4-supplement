# =============================================================================
# Systems Thinking in the AI Era
# https://systemthinkinglab.ai
#
# This code is part of the "Systems Thinking in the AI Era" course series.
# For more information, educational content, and courses, visit:
# https://systemthinkinglab.ai
# =============================================================================

"""
External Entities: Time, External Service, User
These represent forces outside our system that we must respond to

Key Principle: External entities are not building blocks we control,
but rather sources of requirements that drive our system design.
"""

import time
import threading
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from abc import ABC, abstractmethod


# =============================================================================
# TIME EXTERNAL ENTITY
# =============================================================================

class Time:
    """
    Time External Entity - Time-Based Triggers
    
    Represents time-driven events that can trigger system actions.
    Does not execute tasks directly - instead triggers Workers or other building blocks.
    """
    
    def __init__(self, name: str = "system_time"):
        self.name = name
        self.trigger_handlers = {}
        self.scheduled_triggers = {}
        self.running = False
        self.scheduler_thread = None
        self.tick_count = 0
        self.trigger_count = 0
    
    def recurring_trigger(self, interval_seconds: int, start_delay: int = 0):
        """Decorator to register recurring time-based triggers"""
        def decorator(trigger_func):
            trigger_id = trigger_func.__name__
            self.trigger_handlers[trigger_id] = trigger_func
            
            trigger = {
                "id": trigger_id,
                "interval": interval_seconds,
                "callback": trigger_func,
                "next_trigger": datetime.now() + timedelta(seconds=start_delay),
                "trigger_count": 0,
                "last_trigger": None,
                "type": "recurring"
            }
            self.scheduled_triggers[trigger_id] = trigger
            print(f"⏰ Registered recurring trigger '{trigger_id}' every {interval_seconds}s")
            return trigger_func
        return decorator
    
    def once_trigger(self, delay_seconds: int):
        """Decorator to register one-time triggers"""
        def decorator(trigger_func):
            trigger_id = trigger_func.__name__
            self.trigger_handlers[trigger_id] = trigger_func
            
            trigger = {
                "id": trigger_id,
                "callback": trigger_func,
                "trigger_time": datetime.now() + timedelta(seconds=delay_seconds),
                "trigger_count": 0,
                "type": "once"
            }
            self.scheduled_triggers[trigger_id] = trigger
            print(f"⏰ Registered one-time trigger '{trigger_id}' in {delay_seconds}s")
            return trigger_func
        return decorator
    
    def schedule_recurring_trigger(self, trigger_id: str, interval_seconds: int, 
                                 trigger_callback: Callable, start_delay: int = 0):
        """Schedule a recurring trigger (alternative to decorator)"""
        trigger = {
            "id": trigger_id,
            "interval": interval_seconds,
            "callback": trigger_callback,
            "next_trigger": datetime.now() + timedelta(seconds=start_delay),
            "trigger_count": 0,
            "last_trigger": None,
            "type": "recurring"
        }
        self.scheduled_triggers[trigger_id] = trigger
        print(f"⏰ Scheduled recurring trigger '{trigger_id}' every {interval_seconds}s")
    
    def schedule_once_trigger(self, trigger_id: str, delay_seconds: int, trigger_callback: Callable):
        """Schedule a one-time trigger (alternative to decorator)"""
        trigger = {
            "id": trigger_id,
            "callback": trigger_callback,
            "trigger_time": datetime.now() + timedelta(seconds=delay_seconds),
            "trigger_count": 0,
            "type": "once"
        }
        self.scheduled_triggers[trigger_id] = trigger
        print(f"⏰ Scheduled one-time trigger '{trigger_id}' in {delay_seconds}s")
    
    def start_time_monitoring(self):
        """Start monitoring time for triggers"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._time_monitor_loop)
            self.scheduler_thread.start()
            print("⏰ Time monitoring started")
    
    def stop_time_monitoring(self):
        """Stop time monitoring"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        print("⏰ Time monitoring stopped")
    
    def _time_monitor_loop(self):
        """Main time monitoring loop - checks for triggers to fire"""
        while self.running:
            current_time = datetime.now()
            self.tick_count += 1
            
            # Check all scheduled triggers
            triggers_to_remove = []
            for trigger_id, trigger in self.scheduled_triggers.items():
                try:
                    if trigger["type"] == "recurring":
                        if current_time >= trigger["next_trigger"]:
                            # Fire the trigger
                            print(f"⏰ Time triggered: {trigger_id}")
                            trigger["callback"]()
                            trigger["trigger_count"] += 1
                            trigger["last_trigger"] = current_time
                            trigger["next_trigger"] = current_time + timedelta(seconds=trigger["interval"])
                            self.trigger_count += 1
                    
                    elif trigger["type"] == "once":
                        if current_time >= trigger["trigger_time"]:
                            # Fire the trigger
                            print(f"⏰ Time triggered (once): {trigger_id}")
                            trigger["callback"]()
                            trigger["trigger_count"] += 1
                            triggers_to_remove.append(trigger_id)
                            self.trigger_count += 1
                
                except Exception as e:
                    print(f"⏰ Error firing trigger {trigger_id}: {e}")
            
            # Remove completed one-time triggers
            for trigger_id in triggers_to_remove:
                del self.scheduled_triggers[trigger_id]
            
            time.sleep(1)  # Check every second
    
    def get_stats(self) -> Dict:
        """Get time monitoring statistics"""
        active_triggers = len(self.scheduled_triggers)
        total_trigger_fires = sum(trigger["trigger_count"] for trigger in self.scheduled_triggers.values())
        
        return {
            "active_triggers": active_triggers,
            "total_trigger_fires": total_trigger_fires,
            "total_triggers_fired": self.trigger_count,
            "tick_count": self.tick_count,
            "monitoring": self.running
        }
    
    def list_triggers(self) -> List[Dict]:
        """List all scheduled triggers"""
        return [
            {
                "id": trigger["id"],
                "type": trigger["type"],
                "trigger_count": trigger["trigger_count"],
                "next_trigger": trigger.get("next_trigger", trigger.get("trigger_time")),
                "last_trigger": trigger.get("last_trigger")
            }
            for trigger in self.scheduled_triggers.values()
        ]


# =============================================================================
# EXTERNAL SERVICE ENTITY
# =============================================================================

class ExternalService:
    """
    External Service External Entity - Third-Party API Integration
    
    Represents external APIs and services that our system depends on.
    No fixed interface - each external service has its own API contract.
    """
    
    def __init__(self, name: str, base_url: str = None):
        self.name = name
        self.base_url = base_url
        self.call_count = 0
        self.success_count = 0
        self.error_count = 0
        self.response_times = []
        self.last_error = None
        
        # Simulate external service reliability
        self.failure_rate = 0.05  # 5% failure rate for educational purposes
        self.latency_range = (0.1, 2.0)  # Response time range
    
    def make_request(self, endpoint: str, method: str = "GET", 
                    data: Dict = None, headers: Dict = None) -> Dict:
        """
        Make a request to the external service
        
        Note: In real systems, this would use requests.get/post/etc.
        For education, we simulate external service behavior.
        """
        start_time = time.time()
        self.call_count += 1
        
        try:
            # Simulate network latency
            latency = random.uniform(*self.latency_range)
            time.sleep(latency)
            
            # Simulate occasional failures
            if random.random() < self.failure_rate:
                raise Exception(f"External service {self.name} temporarily unavailable")
            
            # Simple successful response
            response = {
                "status": "success",
                "service": self.name,
                "endpoint": endpoint,
                "method": method,
                "request_data": data,
                "response_time": latency,
                "timestamp": datetime.now().isoformat()
            }
            
            # Track success
            self.success_count += 1
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            
            return response
            
        except Exception as e:
            # Track error
            self.error_count += 1
            self.last_error = str(e)
            
            return {
                "status": "error",
                "error": str(e),
                "service": self.name,
                "endpoint": endpoint,
                "response_time": time.time() - start_time
            }
    
    def get_stats(self) -> Dict:
        """Get external service call statistics"""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times) 
            if self.response_times else 0
        )
        
        success_rate = (
            self.success_count / self.call_count 
            if self.call_count > 0 else 0
        )
        
        return {
            "service_name": self.name,
            "total_calls": self.call_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "last_error": self.last_error
        }
    
    def set_reliability(self, failure_rate: float, latency_range: tuple):
        """Configure service reliability for testing scenarios"""
        self.failure_rate = max(0.0, min(1.0, failure_rate))
        self.latency_range = latency_range
        print(f"🌐 {self.name} configured: {failure_rate*100}% failure rate, "
              f"{latency_range[0]}-{latency_range[1]}s latency")


# =============================================================================
# USER EXTERNAL ENTITY
# =============================================================================

class User:
    """
    User External Entity - Human Interaction with the System
    
    Represents human users making requests and expecting responses.
    Can subscribe to queues for real-time updates and async notifications.
    Simulates realistic user behavior patterns and expectations.
    """
    
    def __init__(self, user_id: str, user_type: str = "regular", service_endpoints: Dict = None):
        self.user_id = user_id
        self.user_type = user_type  # regular, power_user, admin, etc.
        self.service_endpoints = service_endpoints or {}  # {service: [endpoints]}
        self.queue_subscriptions = {}  # {queue: [message_types]} - queues this user listens to
        self.received_notifications = []  # Track async notifications received
        self.session_active = False
        self.request_count = 0
        self.last_request_time = None
        self.patience_threshold = 3.0  # seconds before user gets frustrated
        self.requests_per_minute = self._get_usage_pattern()
        
        # User behavior characteristics
        self.preferred_response_time = 1.0  # preferred max response time
        self.error_tolerance = 2  # how many errors before giving up
        self.consecutive_errors = 0
        
        # Real-time notification expectations
        self.notification_patience = 10.0  # how long to wait for async updates
        self.expects_real_time = user_type in ["power_user", "admin"]
    
    def _get_usage_pattern(self) -> int:
        """Get typical usage pattern based on user type"""
        patterns = {
            "light": 5,     # 5 requests per minute
            "regular": 15,  # 15 requests per minute
            "power_user": 45,  # 45 requests per minute
            "admin": 30,    # 30 requests per minute
            "bot": 120      # 120 requests per minute (automated)
        }
        return patterns.get(self.user_type, 15)
    
    def subscribe_to_queue(self, queue, message_types: List[str] = None):
        """
        Subscribe to a queue for real-time notifications
        
        This simulates WebSocket connections, push notifications, or SSE
        where users get async updates about their requests
        """
        if message_types is None:
            message_types = ["*"]  # Subscribe to all message types
        
        self.queue_subscriptions[queue] = message_types
        
        # Register user as subscriber for relevant message types
        for message_type in message_types:
            if message_type == "*":
                queue.register_subscriber("*", self._handle_notification)
            else:
                # Create user-specific message type (e.g., "user_123_order_update")
                user_message_type = f"{self.user_id}_{message_type}"
                queue.register_subscriber(user_message_type, self._handle_notification)
        
        print(f"👤 User {self.user_id} subscribed to {queue.name} for {message_types}")
    
    def _handle_notification(self, notification_data):
        """
        Handle real-time notifications from queues
        
        Simulates user receiving push notifications, WebSocket messages, etc.
        """
        notification = {
            "received_at": datetime.now(),
            "data": notification_data,
            "user_satisfaction": self._analyze_notification_satisfaction(notification_data)
        }
        
        self.received_notifications.append(notification)
        
        print(f"👤 User {self.user_id} received notification: {notification_data}")
        
        # Simulate user reaction to notification
        satisfaction = notification["user_satisfaction"]
        if satisfaction == "satisfied":
            print(f"   ✅ User {self.user_id} is happy with the update")
        elif satisfaction == "impatient":
            print(f"   ⏳ User {self.user_id} thinks this update took too long")
        elif satisfaction == "confused":
            print(f"   ❓ User {self.user_id} doesn't understand this notification")
        
        return {"status": "notification_received", "user_reaction": satisfaction}
    
    def _analyze_notification_satisfaction(self, notification_data) -> str:
        """Analyze user satisfaction with async notifications"""
        
        # Users expect notifications about their own actions
        if isinstance(notification_data, dict):
            if "user_id" in notification_data and notification_data["user_id"] == self.user_id:
                return "satisfied"  # Relevant to them
            elif "status" in notification_data and notification_data["status"] in ["completed", "ready", "finished"]:
                return "satisfied"  # Positive updates
            elif "error" in notification_data or "failed" in str(notification_data):
                return "disappointed"  # Bad news
        
        # Power users and admins expect more detailed notifications
        if self.expects_real_time:
            return "satisfied"
        else:
            return "confused"  # Regular users might not understand technical notifications
    
    def add_service_endpoints(self, service, endpoints: List[str]):
        """Add a service and its endpoints that this user will interact with"""
        self.service_endpoints[service] = endpoints
        print(f"👤 User {self.user_id} now has access to {service.name}: {endpoints}")
    
    def make_async_request(self, service, path: str, data: Dict = None, 
                          expect_notification_queue=None, expected_message_type=None) -> Dict:
        """
        Make a request that expects async response via queue notification
        
        Simulates: AJAX requests, form submissions, file uploads that process in background
        """
        # Make the initial request
        response = self.make_request(service, path, data)
        
        # If expecting async response, track it
        if expect_notification_queue and expected_message_type:
            user_message_type = f"{self.user_id}_{expected_message_type}"
            print(f"👤 User {self.user_id} expecting async notification of type '{user_message_type}'")
            
            # Simulate user waiting for notification
            response["expecting_async_response"] = {
                "queue": expect_notification_queue.name,
                "message_type": user_message_type,
                "started_waiting_at": datetime.now()
            }
        
        return response
    
    def make_request(self, service, path: str, data: Dict = None) -> Dict:
        """
        User makes a request to a specific service endpoint
        
        Tracks user behavior and satisfaction with response times
        """
        request_start = time.time()
        self.request_count += 1
        self.last_request_time = datetime.now()
        
        print(f"👤 User {self.user_id} requesting {service.name}{path}")
        
        # Make the actual request to the service
        response = service.handle_request(path, data)
        
        # Analyze user satisfaction with the response
        response_time = response.get("response_time", 0)
        satisfaction = self._analyze_satisfaction(response, response_time)
        
        # Track consecutive errors
        if response.get("status") != 200:
            self.consecutive_errors += 1
        else:
            self.consecutive_errors = 0
        
        # Add user perspective to response
        response["user_satisfaction"] = satisfaction
        response["user_id"] = self.user_id
        response["service_name"] = service.name
        
        return response
    
    def make_random_request(self) -> Optional[Dict]:
        """
        User makes a random request to one of their available services/endpoints
        
        Simulates realistic user browsing behavior
        """
        if not self.service_endpoints:
            print(f"👤 User {self.user_id} has no services configured")
            return None
        
        # Pick a random service
        service = random.choice(list(self.service_endpoints.keys()))
        
        # Pick a random endpoint from that service
        endpoints = self.service_endpoints[service]
        if not endpoints:
            return None
        
        endpoint = random.choice(endpoints)
        
        # Generate some random data for POST endpoints
        data = None
        if endpoint in ["/login", "/register", "/checkout"]:
            data = {"user_id": self.user_id, "timestamp": time.time()}
        
        return self.make_request(service, endpoint, data)
    
    def _analyze_satisfaction(self, response: Dict, response_time: float) -> Dict:
        """Analyze user satisfaction with the response"""
        satisfaction = {
            "overall": "satisfied",
            "response_time_ok": response_time <= self.preferred_response_time,
            "content_ok": response.get("status") == 200,
            "patience_exceeded": response_time > self.patience_threshold
        }
        
        # Determine overall satisfaction
        if satisfaction["patience_exceeded"]:
            satisfaction["overall"] = "frustrated"
        elif not satisfaction["content_ok"]:
            satisfaction["overall"] = "disappointed"
        elif not satisfaction["response_time_ok"]:
            satisfaction["overall"] = "slightly_annoyed"
        
        return satisfaction
    
    def start_session(self):
        """User starts an active session"""
        self.session_active = True
        print(f"👤 User {self.user_id} started session")
    
    def end_session(self):
        """User ends their session"""
        self.session_active = False
        print(f"👤 User {self.user_id} ended session")
    
    def simulate_user_behavior(self, duration_seconds: int = 60):
        """
        Simulate realistic user behavior over time
        
        Makes random requests to configured services at the user's typical rate
        """
        if not self.service_endpoints:
            print(f"👤 User {self.user_id} has no services to interact with")
            return self.get_stats()
        
        print(f"👤 Starting {duration_seconds}s simulation for user {self.user_id}")
        
        self.start_session()
        start_time = time.time()
        
        # Calculate request interval
        requests_per_second = self.requests_per_minute / 60.0
        base_interval = 1.0 / requests_per_second if requests_per_second > 0 else 60
        
        while (time.time() - start_time) < duration_seconds and self.session_active:
            # Check if user is too frustrated to continue
            if self.consecutive_errors >= self.error_tolerance:
                print(f"👤 User {self.user_id} giving up due to errors")
                break
            
            # Make a random request
            try:
                response = self.make_random_request()
                
                if response:
                    satisfaction = response.get("user_satisfaction", {})
                    
                    if satisfaction.get("overall") == "frustrated":
                        print(f"👤 User {self.user_id} is getting frustrated...")
                
            except Exception as e:
                print(f"👤 User {self.user_id} encountered error: {e}")
                self.consecutive_errors += 1
            
            # Wait before next request (with some randomness)
            interval = base_interval * random.uniform(0.5, 2.0)
            time.sleep(min(interval, duration_seconds - (time.time() - start_time)))
        
        self.end_session()
        return self.get_stats()
    
    def get_stats(self) -> Dict:
        """Get user behavior statistics"""
        return {
            "user_id": self.user_id,
            "user_type": self.user_type,
            "total_requests": self.request_count,
            "total_notifications_received": len(self.received_notifications),
            "session_active": self.session_active,
            "consecutive_errors": self.consecutive_errors,
            "last_request": self.last_request_time.isoformat() if self.last_request_time else None,
            "requests_per_minute": self.requests_per_minute,
            "patience_threshold": self.patience_threshold,
            "configured_services": {service.name: endpoints for service, endpoints in self.service_endpoints.items()},
            "queue_subscriptions": {queue.name: types for queue, types in self.queue_subscriptions.items()},
            "recent_notifications": self.received_notifications[-5:]  # Last 5 notifications
        }


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def demonstrate_external_entities():
    """
    Show how external entities interact with building blocks
    """
    from building_blocks import Service, Worker, Queue  # Import our building blocks
    
    print("=== External Entities Demonstration ===\n")
    
    # Create building blocks
    api_service = Service("demo_api")
    cleanup_worker = Worker("cleanup_worker")
    task_queue = Queue("maintenance_queue")
    
    # Set up service endpoints using decorators
    @api_service.route("/status")
    def get_status():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    @api_service.route("/weather")
    def get_weather():
        # This endpoint will call an external service
        weather_service = ExternalService("weather_api", "https://api.weather.com")
        response = weather_service.make_request("/current", data={"location": "San Francisco"})
        return response
    
    # Set up worker job handlers using decorators
    @cleanup_worker.job_handler("cleanup")
    def cleanup_old_data(job_data):
        print(f"🧹 Worker performing cleanup: {job_data.get('reason', 'no reason')}")
        # In real system, this would clean up old files, logs, etc.
        return {"cleaned_items": random.randint(10, 100)}
    
    @cleanup_worker.job_handler("backup")
    def backup_database(job_data):
        print(f"💾 Worker performing backup: {job_data.get('type', 'incremental')}")
        return {"backup_size_mb": random.randint(100, 1000)}
    
    # 1. TIME ENTITY - Set up time-based triggers using decorators
    print("1. Time Entity - Setting up time-based triggers with decorators:")
    scheduler = Time("system_scheduler")
    
    @scheduler.recurring_trigger(interval_seconds=8, start_delay=2)
    def daily_cleanup_trigger():
        """Time triggers worker to perform cleanup - separation of concerns"""
        job_id = cleanup_worker.submit_job("cleanup", {"reason": "scheduled_by_time"})
        print(f"   ⏰ Time triggered cleanup job: {job_id}")
    
    @scheduler.recurring_trigger(interval_seconds=12, start_delay=5)
    def daily_backup_trigger():
        """Time triggers worker to perform backup"""
        job_id = cleanup_worker.submit_job("backup", {"type": "daily", "reason": "scheduled_by_time"})
        print(f"   ⏰ Time triggered backup job: {job_id}")
    
    @scheduler.once_trigger(delay_seconds=3)
    def startup_check_trigger():
        """One-time startup check"""
        job_id = cleanup_worker.submit_job("cleanup", {"reason": "startup_check"})
        print(f"   ⏰ Time triggered startup check: {job_id}")
    
    scheduler.start_time_monitoring()
    
    # 2. USER ENTITY - Configure user with multiple services and simulate behavior
    print("\n2. User Entity - Configuring user with multiple services:")
    user = User("alice_123", "regular")
    
    # Configure user to interact with different services
    user.add_service_endpoints(api_service, ["/status", "/weather"])
    
    # User makes specific requests
    response1 = user.make_request(api_service, "/status")
    print(f"   👤 User satisfaction with status: {response1['user_satisfaction']['overall']}")
    
    response2 = user.make_request(api_service, "/weather")
    print(f"   👤 User satisfaction with weather: {response2['user_satisfaction']['overall']}")
    
    # User makes random requests
    print("   👤 User making random requests:")
    for i in range(3):
        random_response = user.make_random_request()
        if random_response:
            print(f"      Random request {i+1}: {random_response['service_name']} - {random_response['user_satisfaction']['overall']}")
    
    # 3. EXTERNAL SERVICE - Weather API
    print("\n3. External Service - Weather API integration:")
    weather_api = ExternalService("weather_service")
    weather_response = weather_api.make_request("/forecast", data={"city": "New York"})
    print(f"   🌐 Weather API response: {weather_response['status']}")
    print(f"   🌐 API stats: {weather_api.get_stats()}")
    
    # Let the system run for a bit to see triggers fire
    print("\n=== System Running (watching time triggers and user behavior) ===")
    
    # Start user simulation in a separate thread so we can see both time triggers and user activity
    import threading
    user_simulation = threading.Thread(
        target=lambda: user.simulate_user_behavior(duration_seconds=15), 
        daemon=True
    )
    user_simulation.start()
    
    time.sleep(20)
    
    # Show final stats
    print("\n=== Final Statistics ===")
    print(f"Time Triggers: {scheduler.get_stats()}")
    print(f"User Activity: {user.get_stats()}")
    print(f"Weather API: {weather_api.get_stats()}")
    print(f"Worker Jobs: Completed: {len(cleanup_worker.completed_jobs)}, Failed: {len(cleanup_worker.failed_jobs)}")
    
    # Show some completed jobs
    if cleanup_worker.completed_jobs:
        print("Recent completed jobs:")
        for job in cleanup_worker.completed_jobs[-3:]:  # Show last 3
            print(f"  - {job['type']}: {job['result']} (triggered by: {job['data'].get('reason')})")
    
    # Show registered triggers
    print("Registered time triggers:")
    for trigger in scheduler.list_triggers():
        print(f"  - {trigger['id']}: {trigger['type']} (fired {trigger['trigger_count']} times)")
    
    # Cleanup
    scheduler.stop_time_monitoring()
    cleanup_worker.stop()


if __name__ == "__main__":
    demonstrate_external_entities()