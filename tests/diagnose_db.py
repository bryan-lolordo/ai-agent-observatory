#!/usr/bin/env python3
"""
Observatory Database Diagnostic
Run: python diagnose_db.py
"""

import sqlite3
import json
from pathlib import Path

# Find the database
db_paths = [
    "observatory.db",
    "../ai-agent-observatory/observatory.db",
    "ai-agent-observatory/observatory.db",
]

db_path = None
for p in db_paths:
    if Path(p).exists():
        db_path = p
        break

if not db_path:
    print("❌ Could not find observatory.db")
    print("   Tried:", db_paths)
    exit(1)

print(f"📊 Analyzing: {db_path}\n")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 1. Check table schema
print("=" * 60)
print("1️⃣  TABLE SCHEMA")
print("=" * 60)

cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='llm_calls'")
schema = cursor.fetchone()
if schema:
    print(schema[0][:500] + "..." if len(schema[0]) > 500 else schema[0])

# 2. Count records
print("\n" + "=" * 60)
print("2️⃣  RECORD COUNTS")
print("=" * 60)

cursor = conn.execute("SELECT COUNT(*) FROM llm_calls")
total = cursor.fetchone()[0]
print(f"Total LLM calls: {total}")

# 3. Check quality_evaluation data
print("\n" + "=" * 60)
print("3️⃣  QUALITY EVALUATION DATA")
print("=" * 60)

cursor = conn.execute("""
    SELECT id, operation, quality_evaluation 
    FROM llm_calls 
    WHERE quality_evaluation IS NOT NULL 
    LIMIT 3
""")
rows = cursor.fetchall()

if rows:
    print(f"Found {len(rows)} calls with quality_evaluation:")
    for row in rows:
        print(f"\n  ID: {row['id']}, Op: {row['operation']}")
        qe = row['quality_evaluation']
        if qe:
            try:
                data = json.loads(qe)
                print(f"  Keys: {list(data.keys())}")
                print(f"  Sample: {json.dumps(data, indent=4)[:400]}...")
            except:
                print(f"  Raw: {qe[:200]}...")
else:
    print("❌ NO quality_evaluation data found!")
    
    # Check if column exists
    cursor = conn.execute("PRAGMA table_info(llm_calls)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"\n  Available columns: {columns}")

# 4. Check prompt_breakdown data
print("\n" + "=" * 60)
print("4️⃣  PROMPT BREAKDOWN DATA")
print("=" * 60)

cursor = conn.execute("""
    SELECT id, operation, prompt_breakdown 
    FROM llm_calls 
    WHERE prompt_breakdown IS NOT NULL 
    LIMIT 3
""")
rows = cursor.fetchall()

if rows:
    print(f"Found {len(rows)} calls with prompt_breakdown:")
    for row in rows:
        print(f"\n  ID: {row['id']}, Op: {row['operation']}")
        pb = row['prompt_breakdown']
        if pb:
            try:
                data = json.loads(pb)
                print(f"  Keys: {list(data.keys())}")
                print(f"  Sample: {json.dumps(data, indent=4)[:400]}...")
            except:
                print(f"  Raw: {pb[:200]}...")
else:
    print("❌ NO prompt_breakdown data found!")

# 5. Check routing_decision data
print("\n" + "=" * 60)
print("5️⃣  ROUTING DECISION DATA")
print("=" * 60)

cursor = conn.execute("""
    SELECT id, operation, routing_decision 
    FROM llm_calls 
    WHERE routing_decision IS NOT NULL 
    LIMIT 3
""")
rows = cursor.fetchall()

if rows:
    print(f"Found {len(rows)} calls with routing_decision:")
    for row in rows:
        print(f"\n  ID: {row['id']}, Op: {row['operation']}")
        rd = row['routing_decision']
        if rd:
            try:
                data = json.loads(rd)
                print(f"  Keys: {list(data.keys())}")
            except:
                print(f"  Raw: {rd[:200]}...")
else:
    print("❌ NO routing_decision data found!")

# 6. Check cache_metadata data
print("\n" + "=" * 60)
print("6️⃣  CACHE METADATA DATA")
print("=" * 60)

cursor = conn.execute("""
    SELECT id, operation, cache_metadata 
    FROM llm_calls 
    WHERE cache_metadata IS NOT NULL 
    LIMIT 3
""")
rows = cursor.fetchall()

if rows:
    print(f"Found {len(rows)} calls with cache_metadata:")
    for row in rows:
        print(f"\n  ID: {row['id']}, Op: {row['operation']}")
        cm = row['cache_metadata']
        if cm:
            try:
                data = json.loads(cm)
                print(f"  Keys: {list(data.keys())}")
            except:
                print(f"  Raw: {cm[:200]}...")
else:
    print("❌ NO cache_metadata data found!")

# 7. Check prompt field
print("\n" + "=" * 60)
print("7️⃣  PROMPT DATA (for duplicate detection)")
print("=" * 60)

cursor = conn.execute("""
    SELECT id, operation, prompt 
    FROM llm_calls 
    LIMIT 5
""")
rows = cursor.fetchall()

prompts_with_data = 0
for row in rows:
    prompt = row['prompt']
    if prompt and len(prompt) > 10:
        prompts_with_data += 1
        print(f"  ID {row['id']}: {prompt[:80]}...")
    else:
        print(f"  ID {row['id']}: ❌ Empty or short prompt")

if prompts_with_data == 0:
    print("\n⚠️  Prompts are empty! Cache analyzer can't detect duplicates.")

# 8. Summary
print("\n" + "=" * 60)
print("📋 SUMMARY")
print("=" * 60)

cursor = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN quality_evaluation IS NOT NULL THEN 1 ELSE 0 END) as with_quality,
        SUM(CASE WHEN prompt_breakdown IS NOT NULL THEN 1 ELSE 0 END) as with_breakdown,
        SUM(CASE WHEN routing_decision IS NOT NULL THEN 1 ELSE 0 END) as with_routing,
        SUM(CASE WHEN cache_metadata IS NOT NULL THEN 1 ELSE 0 END) as with_cache,
        SUM(CASE WHEN prompt IS NOT NULL AND LENGTH(prompt) > 10 THEN 1 ELSE 0 END) as with_prompt
    FROM llm_calls
""")
row = cursor.fetchone()

print(f"""
  Total calls:        {row['total']}
  With quality_eval:  {row['with_quality']}
  With prompt_break:  {row['with_breakdown']}
  With routing:       {row['with_routing']}
  With cache:         {row['with_cache']}
  With prompt text:   {row['with_prompt']}
""")

conn.close()
print("\n✅ Diagnostic complete!")