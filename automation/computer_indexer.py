"""
NOVA AI - Computer-Wide Indexer (Type C: Full Computer Discovery)
Discovers all drives and folders, builds persistent SQLite index,
supports semantic search across the entire computer.
"""
import os
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from system.environment_scanner import get_scanner

logger = logging.getLogger(__name__)

# Database location
_INDEX_DB = Path(__file__).parent.parent / "database" / "computer_index.db"

# File extensions to index
_INDEXED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".odt", ".ods", ".odp",
    # Text/Code
    ".txt", ".md", ".csv", ".json", ".xml", ".rtf", ".py", ".js", ".html", ".css",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
    # Audio/Video
    ".mp3", ".mp4", ".avi", ".mkv", ".wav", ".flac",
    # Archives
    ".zip", ".rar", ".7z", ".tar", ".gz",
}

# System folders to skip during scanning
_SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".vscode", ".idea",
    "venv", "env", ".venv", "temp", "tmp", "tmp2",
    "Windows", "ProgramData", "Program Files", "Program Files (x86)",
    "$Recycle.Bin", "System Volume Information",
    "AppData", "Roaming", "Local", "LocalLow",
}

# Max file size to index (100MB)
_MAX_FILE_SIZE = 100 * 1024 * 1024


@dataclass
class IndexedFile:
    """Represents a file in the index."""
    path: str
    name: str
    extension: str
    size: int
    modified_time: float
    created_time: float
    drive: str
    folder_path: str
    is_hidden: bool
    content_hash: Optional[str] = None


class ComputerIndexer:
    """Indexes all files across all drives using SQLite."""
    
    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None
        self.drives: List[str] = []
        
    def connect(self):
        """Connect to the SQLite database."""
        _INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(_INDEX_DB))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        
    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                extension TEXT,
                size INTEGER DEFAULT 0,
                modified_time REAL NOT NULL,
                created_time REAL DEFAULT 0,
                drive TEXT,
                folder_path TEXT,
                is_hidden BOOLEAN DEFAULT 0,
                content_hash TEXT,
                indexed_at TEXT NOT NULL,
                last_scanned REAL NOT NULL
            )
        """)
        
        # Scans log (track when each drive was last scanned)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_log (
                drive TEXT PRIMARY KEY,
                last_scan TEXT NOT NULL,
                files_indexed INTEGER DEFAULT 0,
                files_skipped INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0
            )
        """)
        
        # Indexes for fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_drive ON files(drive)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_path)")
        
        self.conn.commit()
        
    def discover_drives(self) -> List[str]:
        """Discover all available drives using environment scanner."""
        scanner = get_scanner()
        self.drives = scanner.discover_drives()
        return self.drives
    
    def _should_skip_dir(self, dir_path: Path) -> bool:
        """Check if directory should be skipped."""
        # Skip system paths at root level
        if len(dir_path.parts) <= 2:  # C:\ etc
            if any(part in _SKIP_DIRS for part in dir_path.parts):
                return True
        # Always skip hidden/system dirs
        if any(part.startswith('.') and part not in {'.git', '.github'} for part in dir_path.parts):
            return True
        return False
    
    def _scan_drive(self, drive: str) -> List[IndexedFile]:
        """Scan a single drive and return all indexable files."""
        files = []
        drive_path = Path(drive)
        
        if not drive_path.exists() or not drive_path.is_dir():
            return files
            
        logger.info(f"Scanning drive: {drive}")
        
        try:
            for root, dirs, files_in_dir in os.walk(drive):
                root_path = Path(root)
                
                # Skip unwanted directories (modify dirs in-place to prevent recursion)
                dirs[:] = [d for d in dirs if not self._should_skip_dir(root_path / d)]
                
                # Skip if we can't access
                try:
                    root_path.iterdir()
                except PermissionError:
                    continue
                
                for filename in files_in_dir:
                    file_path = root_path / filename
                    
                    try:
                        # Skip if not a file
                        if not file_path.is_file():
                            continue
                        
                        # Skip hidden/system files
                        if file_path.name.startswith('.'):
                            continue
                        
                        # Skip temp files
                        if any(pattern in file_path.name.lower() for pattern in 
                               ['thumbs.db', 'desktop.ini', '.ds_store', '~$']):
                            continue
                        
                        # Check extension
                        ext = file_path.suffix.lower()
                        if ext not in _INDEXED_EXTENSIONS:
                            continue
                        
                        # Check file size
                        try:
                            stat = file_path.stat()
                            if stat.st_size > _MAX_FILE_SIZE:
                                continue
                            if stat.st_size == 0:
                                continue
                        except OSError:
                            continue
                        
                        # Create file record
                        try:
                            created = stat.st_ctime if hasattr(stat, 'st_ctime') else stat.st_mtime
                            files.append(IndexedFile(
                                path=str(file_path.resolve()),
                                name=file_path.name,
                                extension=ext,
                                size=stat.st_size,
                                modified_time=stat.st_mtime,
                                created_time=created,
                                drive=drive,
                                folder_path=str(file_path.parent.resolve()),
                                is_hidden=file_path.name.startswith('.') or bool(stat.st_file_attributes & 2 if hasattr(stat, 'st_file_attributes') else False),
                            ))
                        except Exception:
                            continue
                            
                    except Exception:
                        continue
                        
        except PermissionError:
            logger.warning(f"Permission denied scanning {drive}")
        except Exception as e:
            logger.error(f"Error scanning {drive}: {e}")
            
        return files
    
    def build_index(self, force: bool = False) -> Dict:
        """Build or update the computer-wide index.
        
        Args:
            force: if True, rebuild from scratch ignoring existing index
            
        Returns:
            dict with stats
        """
        if not self.conn:
            self.connect()
            
        if not self.drives:
            self.discover_drives()
            
        stats = {
            "total_drives": len(self.drives),
            "total_files": 0,
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
            "drive_stats": {}
        }
        
        for drive in self.drives:
            drive_stats = self._index_drive(drive, force=force)
            stats["drive_stats"][drive] = drive_stats
            stats["total_files"] += drive_stats.get("indexed", 0) + drive_stats.get("skipped", 0)
            stats["indexed"] += drive_stats.get("indexed", 0)
            stats["skipped"] += drive_stats.get("skipped", 0)
            stats["errors"] += drive_stats.get("errors", 0)
            
        # Save scan log
        self._save_scan_log()
        
        logger.info(f"Index built: {stats['indexed']} files indexed, {stats['skipped']} skipped")
        return stats
    
    def _index_drive(self, drive: str, force: bool = False) -> Dict:
        """Index a single drive."""
        drive_stats = {"indexed": 0, "skipped": 0, "errors": 0}
        cursor = self.conn.cursor()
        
        # Check if we need to rescan
        if not force:
            cursor.execute("SELECT last_scan FROM scan_log WHERE drive = ?", (drive,))
            row = cursor.fetchone()
            if row:
                # Only rescan if last scan was not today
                last_scan = datetime.fromisoformat(row["last_scan"])
                today = datetime.now().date()
                if last_scan.date() == today:
                    logger.info(f"Drive {drive} was scanned today, skipping")
                    return drive_stats
        
        # Scan files
        files = self._scan_drive(drive)
        logger.info(f"Found {len(files)} indexable files on {drive}")
        
        if not files and not force:
            # Just update scan log
            cursor.execute(
                "INSERT OR REPLACE INTO scan_log (drive, last_scan) VALUES (?, ?)",
                (drive, datetime.now().isoformat())
            )
            self.conn.commit()
            return drive_stats
        
        # Index files
        now = datetime.now().isoformat()
        batch = []
        
        for file in files:
            try:
                # Check if already indexed with same mtime
                cursor.execute(
                    "SELECT id, modified_time FROM files WHERE path = ?",
                    (file.path,)
                )
                existing = cursor.fetchone()
                
                if existing and abs(existing["modified_time"] - file.modified_time) < 1.0:
                    # File unchanged, skip
                    drive_stats["skipped"] += 1
                    continue
                
                # Insert or update
                batch.append((
                    file.path, file.name, file.extension, file.size,
                    file.modified_time, file.created_time, file.drive,
                    file.folder_path, file.is_hidden, file.content_hash,
                    now, file.modified_time
                ))
                
            except Exception as e:
                logger.debug(f"Error checking {file.path}: {e}")
                drive_stats["errors"] += 1
                
        # Batch insert/update
        if batch:
            try:
                cursor.executemany("""
                    INSERT OR REPLACE INTO files 
                    (path, name, extension, size, modified_time, created_time,
                     drive, folder_path, is_hidden, content_hash, indexed_at, last_scanned)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                self.conn.commit()
                drive_stats["indexed"] = len(batch)
            except Exception as e:
                logger.error(f"Batch insert error: {e}")
                drive_stats["errors"] += len(batch)
        
        # Update scan log
        cursor.execute(
            "INSERT OR REPLACE INTO scan_log (drive, last_scan, files_indexed, files_skipped, errors) VALUES (?, ?, ?, ?, ?)",
            (drive, now, drive_stats["indexed"], drive_stats["skipped"], drive_stats["errors"])
        )
        self.conn.commit()
        
        return drive_stats
    
    def _save_scan_log(self):
        """Save scan metadata."""
        cursor = self.conn.cursor()
        for drive in self.drives:
            cursor.execute(
                "INSERT OR REPLACE INTO scan_log (drive, last_scan) VALUES (?, ?)",
                (drive, datetime.now().isoformat())
            )
        self.conn.commit()
    
    def get_all_files(self, limit: int = 1000, offset: int = 0) -> List[Dict]:
        """Get all indexed files."""
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, path, name, extension, size, modified_time, created_time,
                   drive, folder_path, is_hidden
            FROM files
            ORDER BY modified_time DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_name(self, query: str, limit: int = 20) -> List[Dict]:
        """Search files by name (partial match)."""
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        query_lower = f"%{query.lower()}%"
        
        cursor.execute("""
            SELECT id, path, name, extension, size, modified_time, drive
            FROM files
            WHERE LOWER(name) LIKE ?
            ORDER BY modified_time DESC
            LIMIT ?
        """, (query_lower, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_extension(self, extension: str, limit: int = 50) -> List[Dict]:
        """Search files by extension."""
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        ext = extension.lower() if extension.startswith('.') else f".{extension.lower()}"
        
        cursor.execute("""
            SELECT id, path, name, extension, size, modified_time, drive
            FROM files
            WHERE extension = ?
            ORDER BY modified_time DESC
            LIMIT ?
        """, (ext, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_folder(self, folder_path: str, limit: int = 50) -> List[Dict]:
        """Search files in a specific folder."""
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        folder_lower = f"%{folder_path.lower()}%"
        
        cursor.execute("""
            SELECT id, path, name, extension, size, modified_time, drive
            FROM files
            WHERE LOWER(folder_path) LIKE ?
            ORDER BY modified_time DESC
            LIMIT ?
        """, (folder_lower, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_drive(self, drive: str, limit: int = 100) -> List[Dict]:
        """Search files on a specific drive."""
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        drive = drive.rstrip('\\/')
        
        cursor.execute("""
            SELECT id, path, name, extension, size, modified_time
            FROM files
            WHERE drive = ?
            ORDER BY modified_time DESC
            LIMIT ?
        """, (drive, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        
        # Total files
        cursor.execute("SELECT COUNT(*) as total FROM files")
        total = cursor.fetchone()["total"]
        
        # By extension
        cursor.execute("""
            SELECT extension, COUNT(*) as count 
            FROM files 
            WHERE extension IS NOT NULL
            GROUP BY extension 
            ORDER BY count DESC 
            LIMIT 10
        """)
        by_extension = {row["extension"]: row["count"] for row in cursor.fetchall()}
        
        # By drive
        cursor.execute("""
            SELECT drive, COUNT(*) as count 
            FROM files 
            GROUP BY drive 
            ORDER BY count DESC
        """)
        by_drive = {row["drive"]: row["count"] for row in cursor.fetchall()}
        
        # Total size
        cursor.execute("SELECT SUM(size) as total_size FROM files")
        total_size = cursor.fetchone()["total_size"] or 0
        
        return {
            "total_files": total,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_extension": by_extension,
            "by_drive": by_drive,
            "index_db": str(_INDEX_DB),
        }
    
    def get_file_by_path(self, path: str) -> Optional[Dict]:
        """Get a single file by exact path."""
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files WHERE path = ?", (path,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_indexer() -> ComputerIndexer:
    """Get global indexer instance."""
    return ComputerIndexer()


def initialize_index(force: bool = False) -> Dict:
    """Initialize the computer index at startup."""
    indexer = get_indexer()
    indexer.connect()
    
    if force or not is_index_ready():
        indexer.discover_drives()
        return indexer.build_index(force=force)
        
    return indexer.get_stats()


def is_index_ready() -> bool:
    """Check if the computer index exists and has data."""
    if not _INDEX_DB.exists():
        return False
    
    try:
        conn = sqlite3.connect(str(_INDEX_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def search_files_semantic(query: str, limit: int = 10) -> List[Dict]:
    """Search the computer index by name (basic semantic-like search).
    
    This is a fast alternative to embedding-based semantic search
    for initial filtering.
    """
    indexer = get_indexer()
    indexer.connect()
    
    # Search by name
    results = indexer.search_by_name(query, limit=limit)
    
    # Convert modified_time to readable format
    for r in results:
        mtime = r.get("modified_time", 0)
        r["modified"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M") if mtime else "unknown"
        
    return results


def find_file_anywhere(filename: str) -> List[Dict]:
    """Find a file anywhere on the computer by exact or partial name."""
    indexer = get_indexer()
    indexer.connect()
    return indexer.search_by_name(filename, limit=20)


def get_all_drives() -> List[str]:
    """Get list of all drives."""
    indexer = get_indexer()
    if not indexer.drives:
        indexer.discover_drives()
    return indexer.drives


def get_index_stats() -> Dict:
    """Get statistics about the computer index."""
    indexer = get_indexer()
    indexer.connect()
    return indexer.get_stats()


if __name__ == "__main__":
    # Test
    print("=" * 60)
    print("NOVA Computer-Wide Indexer - Test")
    print("=" * 60)
    
    indexer = ComputerIndexer()
    indexer.connect()
    
    print("\n[1] Discovering Drives...")
    drives = indexer.discover_drives()
    print(f"Found {len(drives)} drives: {drives}")
    
    print("\n[2] Building Index...")
    stats = indexer.build_index(force=False)
    print(f"Stats: {stats}")
    
    print("\n[3] Searching...")
    results = search_files_semantic("assignment", limit=5)
    print(f"Found {len(results)} files matching 'assignment':")
    for r in results[:5]:
        print(f"  - {r['name']} ({r['path']})")
    
    print("\n[4] Index Stats...")
    stats = get_index_stats()
    print(f"Total files indexed: {stats['total_files']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"By drive: {stats['by_drive']}")
    
    indexer.disconnect()
    print("\nDone!")