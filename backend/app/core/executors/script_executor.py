"""ScriptExecutor - executes Python scripts in subprocess."""

import subprocess
import threading
import os
import sys
import re
import select
from typing import Optional, Dict, Any, List
from datetime import datetime
from time import time

from .base import BaseExecutor, ExecutorResult, ExecutorLog


class ScriptExecutor(BaseExecutor):
    """Execute Python scripts in a subprocess with environment variable injection."""
    
    def __init__(self):
        super().__init__()
        self.process: Optional[subprocess.Popen] = None
        self.stdout_lines: List[str] = []
        self.stderr_lines: List[str] = []
        self._start_time: float = 0
    
    def start(
        self,
        script_content: str,
        device: Any = None,
        project: Any = None,
        env_vars: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> subprocess.Popen:
        """
        Start script execution in a subprocess.
        
        Args:
            script_content: Python script content to execute
            device: Device object with serial attribute
            project: Project object with app_id attribute
            env_vars: Additional environment variables
        
        Returns:
            Popen object for the running process
        """
        import tempfile
        
        # Create temp script file
        with tempfile.NamedTemporaryFile(
            suffix='.py', delete=False, mode='w', encoding='utf-8'
        ) as temp_script:
            temp_script.write(script_content)
            script_path = temp_script.name
        
        # Build environment variables
        env = os.environ.copy()
        
        # Inject device info
        if device and hasattr(device, 'serial'):
            env["DEVICE_SERIAL"] = device.serial
        if project and hasattr(project, 'app_id'):
            env["APP_PACKAGE"] = project.app_id
        
        # Add custom env vars
        if env_vars:
            env.update(env_vars)
        
        # Ensure project root is in PYTHONPATH
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{project_root}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = project_root
        
        # Build command
        command = [sys.executable, script_path]
        
        self._log(f"Starting script execution: {command}")
        self._log(f"Device serial: {env.get('DEVICE_SERIAL', 'N/A')}")
        self._log(f"App package: {env.get('APP_PACKAGE', 'N/A')}")
        
        # Start subprocess
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=project_root
        )
        
        self._start_time = time()
        
        # Start stderr reader thread
        stderr_thread = threading.Thread(
            target=self._read_stderr,
            daemon=True
        )
        stderr_thread.start()
        
        return self.process
    
    def _read_stderr(self):
        """Read stderr in a separate thread to prevent buffer blocking."""
        if not self.process:
            return
        
        try:
            for line in iter(self.process.stderr.readline, ''):
                if line:
                    self.stderr_lines.append(line)
                    self._log(line.rstrip(), "STDERR")
        except Exception:
            pass
    
    def wait(
        self,
        cancel_check: Optional[callable] = None
    ) -> ExecutorResult:
        """
        Wait for execution to complete with cancellation support.
        
        Args:
            cancel_check: Callback function that returns True if execution should be cancelled
        
        Returns:
            ExecutorResult with execution details
        """
        if not self.process:
            return ExecutorResult(
                status="failed",
                error_message="No process started"
            )
        
        stdout_lines: List[str] = []
        self._log("Waiting for process to complete...")
        
        try:
            while True:
                # Check for cancellation first (every iteration)
                if cancel_check and cancel_check():
                    self._log("Cancellation requested, killing process...", "WARNING")
                    self.process.kill()
                    duration_ms = int((time() - self._start_time) * 1000)
                    return ExecutorResult(
                        status="cancelled",
                        logs=self.logs,
                        stdout=''.join(stdout_lines),
                        stderr=''.join(self.stderr_lines),
                        exit_code=-1,
                        duration_ms=duration_ms
                    )
                
                # Check if process has finished
                if self.process.poll() is not None:
                    self._log(f"Process finished with poll: {self.process.poll()}")
                    break
                
                # Non-blocking read with timeout to allow cancellation checks
                try:
                    ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                    if ready:
                        line = self.process.stdout.readline()
                        if line:
                            stdout_lines.append(line)
                            self._log(line.rstrip(), "STDOUT")
                except (select.error, IOError):
                    # Handle cases where stdout is not selectable
                    break
                
                # Small sleep to prevent busy waiting
                import time as time_module
                time_module.sleep(0.05)
            
            # Read any remaining output
            try:
                remaining_output = self.process.stdout.read()
                if remaining_output:
                    stdout_lines.append(remaining_output)
                    self._log(remaining_output.rstrip(), "STDOUT")
            except Exception:
                pass
            
            # Wait for process to fully terminate
            exit_code = self.process.wait()
            
            duration_ms = int((time() - self._start_time) * 1000)
            stdout = ''.join(stdout_lines)
            stderr = ''.join(self.stderr_lines)
            
            # Parse error if any
            error_message = self._parse_stderr_error(stderr)
            
            # Determine status
            if exit_code == 0:
                status = "success"
                self._log(f"Process completed successfully (exit code: {exit_code})")
            else:
                status = "failed"
                self._log(f"Process failed with exit code: {exit_code}", "ERROR")
            
            return ExecutorResult(
                status=status,
                logs=self.logs,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_ms=duration_ms,
                error_message=error_message
            )
        
        except Exception as e:
            duration_ms = int((time() - self._start_time) * 1000)
            self._log(f"Error during wait: {str(e)}", "ERROR")
            return ExecutorResult(
                status="failed",
                logs=self.logs,
                stdout=''.join(stdout_lines),
                stderr=''.join(self.stderr_lines),
                exit_code=-2,
                duration_ms=duration_ms,
                error_message=str(e)
            )
    
    def _parse_stderr_error(self, stderr: str) -> Optional[str]:
        """
        Parse stderr to extract human-readable error messages.
        
        Currently supports:
        - ModuleNotFoundError
        """
        # Check for missing module
        match = re.search(r"ModuleNotFoundError: No module named ['\"](\w+)['\"]", stderr)
        if match:
            return f"模块 '{match.group(1)}' 未安装！请使用 pip install {match.group(1)} 安装。"
        
        return None
    
    def kill(self):
        """Kill the running process."""
        if self.process and self.process.poll() is None:
            self.process.kill()
            self._log("Process killed", "WARNING")
