"""Persistent project memory, decisions, and conventions manager."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProjectMemoryItem(BaseModel):
    id: str
    project_id: str
    category: str  # 'architecture', 'convention', 'decision', 'dependency'
    title: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemoryStore:
    """Manages persistent project memories and contextual guidelines."""

    def __init__(self):
        self._memories: Dict[str, List[ProjectMemoryItem]] = {}

    def add_memory(self, project_id: str, category: str, title: str, content: str) -> ProjectMemoryItem:
        import uuid
        item = ProjectMemoryItem(
            id=str(uuid.uuid4()),
            project_id=project_id,
            category=category,
            title=title,
            content=content,
        )
        if project_id not in self._memories:
            self._memories[project_id] = []
        self._memories[project_id].append(item)
        return item

    def get_project_memories(self, project_id: str, category: Optional[str] = None) -> List[ProjectMemoryItem]:
        items = self._memories.get(project_id, [])
        if category:
            return [it for it in items if it.category.lower() == category.lower()]
        return items

    def format_memory_context(self, project_id: str) -> str:
        """Format persistent memory into context string for agent reasoning."""
        items = self.get_project_memories(project_id)
        if not items:
            return "No prior memory recorded for this project."

        sections = []
        for it in items:
            sections.append(f"- [{it.category.upper()}] {it.title}: {it.content}")
        return "\n".join(sections)


# Singleton memory store
memory_store = MemoryStore()
