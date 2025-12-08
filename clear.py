#!/usr/bin/env python3
"""
Clear Career Copilot project data from Observatory
Run from ai-agent-observatory directory
"""

import sqlite3
from pathlib import Path

# Database is in same directory as script
OBSERVATORY_DB_PATH = Path(__file__).parent / "observatory.db"
PROJECT_NAME = "Career Copilot"

def clear_project_data():
    """Delete all data for Career Copilot project."""
    
    if not OBSERVATORY_DB_PATH.exists():
        print(f"❌ Database not found at: {OBSERVATORY_DB_PATH}")
        return
    
    print(f"🗑️  Clearing all data for project: {PROJECT_NAME}")
    print(f"   Database: {OBSERVATORY_DB_PATH}")
    
    conn = sqlite3.connect(OBSERVATORY_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get session IDs for Career Copilot
        cursor.execute("SELECT id FROM sessions WHERE project_name = ?", (PROJECT_NAME,))
        session_ids = [row[0] for row in cursor.fetchall()]
        
        if not session_ids:
            print(f"\n✅ No data found for project '{PROJECT_NAME}'")
            conn.close()
            return
        
        # Count what will be deleted
        placeholders = ','.join('?' * len(session_ids))
        cursor.execute(f"SELECT COUNT(*) FROM llm_calls WHERE session_id IN ({placeholders})", session_ids)
        calls_count = cursor.fetchone()[0]
        
        sessions_count = len(session_ids)
        
        print(f"\nFound for '{PROJECT_NAME}':")
        print(f"  - {calls_count} LLM calls")
        print(f"  - {sessions_count} sessions")
        
        # Confirm
        response = input("\nDelete this data? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Cancelled")
            conn.close()
            return
        
        # Delete LLM calls first (foreign key relationship)
        cursor.execute(f"DELETE FROM llm_calls WHERE session_id IN ({placeholders})", session_ids)
        deleted_calls = cursor.rowcount
        
        # Delete sessions
        cursor.execute("DELETE FROM sessions WHERE project_name = ?", (PROJECT_NAME,))
        deleted_sessions = cursor.rowcount
        
        conn.commit()
        
        print(f"\n✅ Deleted:")
        print(f"  - {deleted_calls} LLM calls")
        print(f"  - {deleted_sessions} sessions")
        
        # Show what's left overall
        cursor.execute("SELECT COUNT(*) FROM llm_calls")
        remaining_calls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions")
        remaining_sessions = cursor.fetchone()[0]
        
        print(f"\n📊 Remaining (all projects):")
        print(f"  - {remaining_calls} LLM calls")
        print(f"  - {remaining_sessions} sessions")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    clear_project_data()