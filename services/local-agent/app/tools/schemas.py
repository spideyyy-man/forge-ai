"""Tool I/O schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ListDirectoryInput(BaseModel):
    path: str
    recursive: bool = False
    max_depth: int = 3


class ReadFileInput(BaseModel):
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None


class WriteFileInput(BaseModel):
    path: str
    content: str
    create_parents: bool = False


class ExecuteCommandInput(BaseModel):
    command: str
    cwd: Optional[str] = None
    timeout: Optional[int] = None


class SearchTextInput(BaseModel):
    root_path: str
    query: str
    file_patterns: Optional[List[str]] = None
    max_results: int = 100


class GitStatusInput(BaseModel):
    repo_path: str


class RunTestsInput(BaseModel):
    project_path: str
    test_command: Optional[str] = None
