"""TaskDispatcher - coordinates task execution across multiple devices."""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
import time
import os

from .script_executor import ScriptExecutor
from .base import ExecutorResult


class TaskDispatcher:
    """Task dispatcher for managing multi-device concurrent execution."""
    
    def __init__(self):
        self._cancel_flags: Dict[str, bool] = {}
        self._task_processes: Dict[str, List] = {}
    
    def is_cancelled(self, task_id: str) -> bool:
        """Check if a task has been cancelled."""
        return self._cancel_flags.get(task_id, False)
    
    def cancel_task(self, task_id: str):
        """Cancel a running task."""
        self._cancel_flags[task_id] = True
        
        # Kill all processes associated with this task
        processes = self._task_processes.get(task_id, [])
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        
        self._task_processes.pop(task_id, None)
    
    def _record_process(self, task_id: str, process):
        """Record a process associated with a task."""
        if task_id not in self._task_processes:
            self._task_processes[task_id] = []
        self._task_processes[task_id].append(process)
    
    async def dispatch(
        self,
        task_id: str,
        script_content: str,
        devices: List[Any],
        project: Any = None,
        model_config: Optional[Dict] = None,
        on_log: Optional[Callable[[str, str, str], None]] = None
    ) -> Dict[str, ExecutorResult]:
        """
        Dispatch a task to multiple devices concurrently.
        
        Args:
            task_id: Unique task identifier
            script_content: Python script content to execute
            devices: List of device objects to execute on
            project: Project object containing app info
            model_config: Model configuration for environment injection
            on_log: Callback for logging
        
        Returns:
            Dictionary mapping device serials to execution results
        """
        if on_log:
            await asyncio.get_event_loop().run_in_executor(
                None, on_log, task_id, "INFO", f"Starting task dispatch to {len(devices)} devices"
            )
        
        # Initialize cancel flag
        self._cancel_flags[task_id] = False
        
        results: Dict[str, ExecutorResult] = {}
        
        if not devices:
            if on_log:
                await asyncio.get_event_loop().run_in_executor(
                    None, on_log, task_id, "WARNING", "No devices specified for task"
                )
            return results
        
        # Execute on each device concurrently using ThreadPool
        with ThreadPoolExecutor(max_workers=len(devices)) as executor:
            futures = {}
            
            for device in devices:
                future = executor.submit(
                    self._execute_on_device,
                    task_id,
                    script_content,
                    device,
                    project,
                    model_config,
                    on_log
                )
                futures[future] = device.serial if hasattr(device, 'serial') else str(device)
            
            # Collect results as they complete
            for future in as_completed(futures):
                device_serial = futures[future]
                try:
                    result = future.result()
                    results[device_serial] = result
                    
                    if on_log:
                        status = result.status
                        msg = f"Device {device_serial} completed with status: {status}"
                        level = "INFO" if status == "success" else "ERROR"
                        await asyncio.get_event_loop().run_in_executor(
                            None, on_log, task_id, level, msg
                        )
                except Exception as e:
                    if on_log:
                        await asyncio.get_event_loop().run_in_executor(
                            None, on_log, task_id, "ERROR", 
                            f"Device {device_serial} failed with exception: {str(e)}"
                        )
                    results[device_serial] = ExecutorResult(
                        status="failed",
                        error_message=str(e),
                        duration_ms=0
                    )
        
        # Cleanup
        self._cancel_flags.pop(task_id, None)
        
        return results
    
    def _execute_on_device(
        self,
        task_id: str,
        script_content: str,
        device: Any,
        project: Any = None,
        model_config: Optional[Dict] = None,
        on_log: Optional[Callable[[str, str, str], None]] = None
    ) -> ExecutorResult:
        """
        Execute script on a single device.
        
        This runs in a separate thread.
        """
        executor = ScriptExecutor()
        
        # Build environment variables
        env_vars = {}
        
        # Add model config to environment
        if model_config:
            env_vars['PHONE_AGENT_BASE_URL'] = model_config.get('base_url', '')
            env_vars['PHONE_AGENT_MODEL'] = model_config.get('model_name', '')
            env_vars['PHONE_AGENT_API_KEY'] = model_config.get('api_key', '')
            env_vars['PHONE_AGENT_PROVIDER'] = model_config.get('provider', '')
        
        # Add device ID
        if device and hasattr(device, 'serial'):
            env_vars['PHONE_AGENT_DEVICE_ID'] = device.serial
        
        try:
            # Start execution
            process = executor.start(
                script_content=script_content,
                device=device,
                project=project,
                env_vars=env_vars
            )
            
            # Record process for cancellation
            self._record_process(task_id, process)
            
            # Define cancel check callback
            def cancel_check():
                return self.is_cancelled(task_id)
            
            # Wait for completion
            result = executor.wait(cancel_check=cancel_check)
            
            return result
            
        except Exception as e:
            return ExecutorResult(
                status="failed",
                error_message=str(e),
                duration_ms=0
            )
