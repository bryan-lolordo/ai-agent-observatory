"""
Backfill system_prompt and user_message from metadata JSON.
Run once after updating collector.py

Usage:
    python scripts/backfill_prompt_fields.py
"""

from observatory.storage import ObservatoryStorage, LLMCallDB
from sqlalchemy.orm import Session as DBSession


def backfill():
    """Backfill system_prompt and user_message from metadata."""
    
    storage = ObservatoryStorage
    db: DBSession = storage.SessionLocal()
    
    try:
        # Find calls where system_prompt or user_message is NULL but metadata exists
        calls = db.query(LLMCallDB).filter(
            LLMCallDB.meta_data.isnot(None),
            (LLMCallDB.system_prompt.is_(None)) | (LLMCallDB.user_message.is_(None))
        ).all()
        
        print(f"Found {len(calls)} calls to check")
        
        updated = 0
        for call in calls:
            changed = False
            metadata = call.meta_data or {}
            
            # Backfill system_prompt
            if call.system_prompt is None and 'system_prompt' in metadata:
                call.system_prompt = metadata['system_prompt']
                changed = True
            
            # Backfill user_message
            if call.user_message is None and 'user_message' in metadata:
                call.user_message = metadata['user_message']
                changed = True
            
            if changed:
                updated += 1
                if updated % 100 == 0:
                    print(f"  Updated {updated} calls...")
        
        db.commit()
        print(f"\n✅ Done! Updated {updated} calls")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill()