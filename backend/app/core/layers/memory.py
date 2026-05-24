"""Memory layer for the Agent architecture."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import os
import time


@dataclass
class MemoryItem:
    """Single memory item."""
    timestamp: float
    type: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class MemoryLayer:
    """Memory layer - stores and retrieves agent experiences."""
    
    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = memory_dir
        self.memories: List[MemoryItem] = []
        os.makedirs(memory_dir, exist_ok=True)
    
    def add_memory(self, item_type: str, content: Dict[str, Any], metadata: Optional[Dict] = None):
        """Add a memory item."""
        item = MemoryItem(
            timestamp=time.time(),
            type=item_type,
            content=content,
            metadata=metadata
        )
        self.memories.append(item)
        self._persist_memory(item)
    
    def _persist_memory(self, item: MemoryItem):
        """Persist memory to disk."""
        filename = f"memory_{int(item.timestamp)}.json"
        filepath = os.path.join(self.memory_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": item.timestamp,
                "type": item.type,
                "content": item.content,
                "metadata": item.metadata
            }, f, ensure_ascii=False, indent=2)
    
    def recall(self, query: Optional[str] = None, limit: int = 10) -> List[MemoryItem]:
        """Recall memories based on query."""
        recent = sorted(self.memories, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        if query:
            return [m for m in recent if query.lower() in str(m.content).lower()]
        return recent
    
    def recall_by_type(self, item_type: str, limit: int = 10) -> List[MemoryItem]:
        """Recall memories by type."""
        filtered = [m for m in self.memories if m.type == item_type]
        return sorted(filtered, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_history_for_decision(self) -> List[Dict[str, Any]]:
        """Get recent history in format suitable for decision making."""
        recent = self.recall(limit=5)
        history = []
        for item in recent:
            if item.type == "action":
                history.append({
                    "role": "assistant",
                    "content": item.content.get("action", "")
                })
            elif item.type == "observation":
                history.append({
                    "role": "user",
                    "content": item.content.get("observation", "")
                })
        return history
    
    def clear_memory(self):
        """Clear all memories."""
        self.memories = []
        for file in os.listdir(self.memory_dir):
            if file.startswith("memory_") and file.endswith(".json"):
                os.remove(os.path.join(self.memory_dir, file))
    
    def get_memory_stats(self) -> Dict[str, int]:
        """Get statistics about stored memories."""
        stats = {"total": len(self.memories)}
        for item in self.memories:
            stats[item.type] = stats.get(item.type, 0) + 1
        return stats
