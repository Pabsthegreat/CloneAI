"""
CloneAI Artifacts Management

Centralized system for managing generated files (images, documents, etc.)
All artifacts are stored in ~/.clai/artifacts/ with subdirectories by type.
"""

import os
from pathlib import Path
from typing import Optional, List
import datetime


class ArtifactsManager:
    """
    Manages the centralized artifacts directory structure.
    
    Directory structure:
    ~/.clai/artifacts/
        ├── images/       # Generated images (DALL-E, etc.)
        ├── documents/    # PDFs, DOCX, PPTX, etc.
        ├── audio/        # Generated audio/speech files
        ├── temp/         # Temporary files
        └── exports/      # Exported data (CSVs, etc.)
    """
    
    BASE_DIR = Path.home() / ".clai" / "artifacts"
    
    # Artifact type subdirectories
    IMAGES_DIR = BASE_DIR / "images"
    DOCUMENTS_DIR = BASE_DIR / "documents"
    AUDIO_DIR = BASE_DIR / "audio"
    TEMP_DIR = BASE_DIR / "temp"
    EXPORTS_DIR = BASE_DIR / "exports"
    
    @classmethod
    def initialize(cls) -> None:
        """Create all artifact directories if they don't exist."""
        for directory in [
            cls.BASE_DIR,
            cls.IMAGES_DIR,
            cls.DOCUMENTS_DIR,
            cls.AUDIO_DIR,
            cls.TEMP_DIR,
            cls.EXPORTS_DIR
        ]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create .gitignore in artifacts directory
        gitignore_path = cls.BASE_DIR / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, 'w') as f:
                f.write("# Ignore all generated artifacts\n*\n!.gitignore\n")
    
    @classmethod
    def get_artifacts_dir(cls) -> Path:
        """Get the base artifacts directory path."""
        cls.initialize()
        return cls.BASE_DIR
    
    @classmethod
    def get_images_dir(cls) -> Path:
        """Get the images directory path."""
        cls.initialize()
        return cls.IMAGES_DIR
    
    @classmethod
    def get_documents_dir(cls) -> Path:
        """Get the documents directory path."""
        cls.initialize()
        return cls.DOCUMENTS_DIR
    
    @classmethod
    def get_audio_dir(cls) -> Path:
        """Get the audio directory path."""
        cls.initialize()
        return cls.AUDIO_DIR
    
    @classmethod
    def get_temp_dir(cls) -> Path:
        """Get the temporary files directory path."""
        cls.initialize()
        return cls.TEMP_DIR
    
    @classmethod
    def get_exports_dir(cls) -> Path:
        """Get the exports directory path."""
        cls.initialize()
        return cls.EXPORTS_DIR
    
    @classmethod
    def get_artifact_path(cls, filename: str, artifact_type: str = "documents") -> Path:
        """
        Get full path for an artifact file.
        
        Args:
            filename: Name of the file
            artifact_type: Type of artifact (images, documents, audio, temp, exports)
        
        Returns:
            Full path to the artifact file
        """
        cls.initialize()
        
        type_dirs = {
            "images": cls.IMAGES_DIR,
            "documents": cls.DOCUMENTS_DIR,
            "audio": cls.AUDIO_DIR,
            "temp": cls.TEMP_DIR,
            "exports": cls.EXPORTS_DIR
        }
        
        artifact_dir = type_dirs.get(artifact_type, cls.DOCUMENTS_DIR)
        return artifact_dir / filename
    
    @classmethod
    def resolve_file_path(cls, file_reference: str) -> Optional[Path]:
        """
        Resolve a file reference to its actual path.
        
        Checks in order:
        1. Absolute path (if exists)
        2. Current working directory
        3. All artifact subdirectories
        
        Args:
            file_reference: Filename or path reference
        
        Returns:
            Resolved Path object or None if not found
        """
        cls.initialize()
        
        # If it's an absolute path and exists, return it
        path = Path(file_reference)
        if path.is_absolute() and path.exists():
            return path
        
        # Check current working directory
        cwd_path = Path.cwd() / file_reference
        if cwd_path.exists():
            return cwd_path
        
        # Check all artifact subdirectories
        for artifact_dir in [
            cls.DOCUMENTS_DIR,
            cls.IMAGES_DIR,
            cls.AUDIO_DIR,
            cls.EXPORTS_DIR,
            cls.TEMP_DIR,
            cls.BASE_DIR  # Also check base dir
        ]:
            artifact_path = artifact_dir / file_reference
            if artifact_path.exists():
                return artifact_path
        
        return None
    
    @classmethod
    def list_artifacts(cls, artifact_type: Optional[str] = None, pattern: str = "*") -> List[Path]:
        """
        List all artifacts in a directory.
        
        Args:
            artifact_type: Specific type to list (images, documents, etc.), or None for all
            pattern: Glob pattern (default: "*" for all files)
        
        Returns:
            List of Path objects for matching files
        """
        cls.initialize()
        
        if artifact_type:
            type_dirs = {
                "images": cls.IMAGES_DIR,
                "documents": cls.DOCUMENTS_DIR,
                "audio": cls.AUDIO_DIR,
                "temp": cls.TEMP_DIR,
                "exports": cls.EXPORTS_DIR
            }
            search_dir = type_dirs.get(artifact_type, cls.BASE_DIR)
            return sorted(search_dir.glob(pattern))
        else:
            # List all artifacts from all subdirectories
            all_artifacts = []
            for subdir in [cls.IMAGES_DIR, cls.DOCUMENTS_DIR, cls.AUDIO_DIR, cls.EXPORTS_DIR]:
                all_artifacts.extend(subdir.glob(pattern))
            return sorted(all_artifacts)
    
    @classmethod
    def get_recent_artifacts(cls, artifact_type: Optional[str] = None, limit: int = 10) -> List[Path]:
        """
        Get most recently created/modified artifacts.
        
        Args:
            artifact_type: Specific type or None for all
            limit: Maximum number of files to return
        
        Returns:
            List of Path objects sorted by modification time (newest first)
        """
        artifacts = cls.list_artifacts(artifact_type)
        artifacts.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return artifacts[:limit]
    
    @classmethod
    def clean_temp_files(cls, older_than_hours: int = 24) -> int:
        """
        Clean temporary files older than specified hours.
        
        Args:
            older_than_hours: Delete files older than this many hours
        
        Returns:
            Number of files deleted
        """
        cls.initialize()
        
        cutoff_time = datetime.datetime.now().timestamp() - (older_than_hours * 3600)
        deleted_count = 0
        
        for temp_file in cls.TEMP_DIR.glob("*"):
            if temp_file.is_file() and temp_file.stat().st_mtime < cutoff_time:
                temp_file.unlink()
                deleted_count += 1
        
        return deleted_count
    
    @classmethod
    def get_artifact_info(cls, filename: str) -> Optional[dict]:
        """
        Get information about an artifact file.
        
        Returns:
            Dict with file info or None if not found
        """
        file_path = cls.resolve_file_path(filename)
        if not file_path or not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            "path": str(file_path),
            "name": file_path.name,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "type": file_path.suffix[1:] if file_path.suffix else "unknown"
        }


# Initialize on import
ArtifactsManager.initialize()


def get_artifacts_dir() -> Path:
    """Convenience function to get artifacts directory."""
    return ArtifactsManager.get_artifacts_dir()


def get_artifact_path(filename: str, artifact_type: str = "documents") -> Path:
    """Convenience function to get artifact path."""
    return ArtifactsManager.get_artifact_path(filename, artifact_type)


def resolve_file(file_reference: str) -> Optional[Path]:
    """Convenience function to resolve file reference."""
    return ArtifactsManager.resolve_file_path(file_reference)


__all__ = [
    "ArtifactsManager",
    "get_artifacts_dir",
    "get_artifact_path",
    "resolve_file"
]
