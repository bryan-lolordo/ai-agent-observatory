import sqlite3
import json
import pandas as pd
import sys

# Fix encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

db_path = 'observatory.db'

print("="*80)
print("COMPLETE SCHEMA AUDIT - AI Agent Observatory")
print("="*80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ============================================================================
# PART 1: Get all columns in llm_calls table
# ============================================================================
cursor.execute("PRAGMA table_info(llm_calls)")
columns = cursor.fetchall()

print(f"\nPART 1: TOP-LEVEL COLUMNS ({len(columns)} total)")
print("="*80)
print(f"{'#':<4} {'Column Name':<35} {'Type':<15} {'NotNull':<8}")
print("-"*80)

column_names = []
json_columns = []

for col in columns:
    cid, name, dtype, notnull, default_val, pk = col
    column_names.append(name)
    if dtype == 'JSON':
        json_columns.append(name)
    
    status = "PK" if pk else ("NOT NULL" if notnull else "")
    print(f"{cid:<4} {name:<35} {dtype:<15} {status:<8}")

# ============================================================================
# PART 2: Sample data from JSON columns to see structure
# ============================================================================
print(f"\nPART 2: JSON COLUMN CONTENTS ({len(json_columns)} JSON columns)")
print("="*80)

# Get a sample row with data
cursor.execute("SELECT * FROM llm_calls WHERE id IS NOT NULL LIMIT 1")
sample_row = cursor.fetchone()

if sample_row:
    # Map column names to values
    row_dict = dict(zip(column_names, sample_row))
    
    for json_col in json_columns:
        print(f"\n[{json_col}]")
        print("-"*80)
        
        value = row_dict.get(json_col)
        if value:
            try:
                parsed = json.loads(value)
                print(json.dumps(parsed, indent=2))
            except:
                print(f"  (Not JSON or empty)")
        else:
            print(f"  (NULL or empty)")

# ============================================================================
# PART 3: Check which columns have data
# ============================================================================
print(f"\nPART 3: COLUMN POPULATION ANALYSIS")
print("="*80)

cursor.execute(f"SELECT COUNT(*) FROM llm_calls")
total_rows = cursor.fetchone()[0]

print(f"Total rows: {total_rows}\n")
print(f"{'Column Name':<35} {'Non-NULL':<10} {'%':<8} {'Type':<10}")
print("-"*80)

population_report = []

for col_name in column_names:
    cursor.execute(f"SELECT COUNT(*) FROM llm_calls WHERE {col_name} IS NOT NULL")
    non_null = cursor.fetchone()[0]
    pct = (non_null / total_rows * 100) if total_rows > 0 else 0
    
    # Get column type
    col_type = next((c[2] for c in columns if c[1] == col_name), "")
    
    # Status indicator
    if pct >= 90:
        status = "FULL"
    elif pct >= 50:
        status = "PARTIAL"
    elif pct > 0:
        status = "RARE"
    else:
        status = "EMPTY"
    
    print(f"{status:7s} {col_name:<33} {non_null:<10} {pct:>6.1f}%  {col_type:<10}")
    population_report.append((col_name, pct, status, col_type))

# ============================================================================
# PART 4: Key fields for 7 Data Stories
# ============================================================================
print(f"\nPART 4: CRITICAL FIELDS FOR DATA STORIES")
print("="*80)

story_fields = {
    'Story 1 - Latency': ['latency_ms', 'operation', 'agent_name'],
    'Story 2 - Cache': ['system_prompt', 'user_message', 'cache_metadata'],
    'Story 3 - Routing': ['model_name', 'routing_decision', 'latency_ms'],
    'Story 4 - Quality': ['quality_evaluation', 'success', 'error'],
    'Story 5 - Token Imbalance': ['prompt_tokens', 'completion_tokens', 'system_prompt_tokens', 'user_message_tokens'],
    'Story 6 - Prompt Waste': ['system_prompt', 'system_prompt_tokens', 'prompt_breakdown'],
    'Story 7 - Cost': ['total_cost', 'operation', 'agent_name', 'model_name'],
}

for story, fields in story_fields.items():
    print(f"\n{story}:")
    for field in fields:
        if field in column_names:
            print(f"  [COLUMN] {field}")
        else:
            print(f"  [MISSING/JSON] {field}")

# ============================================================================
# PART 5: Summary by category
# ============================================================================
print(f"\nPART 5: SUMMARY BY POPULATION")
print("="*80)

full = [col for col, pct, status, _ in population_report if status == "FULL"]
partial = [col for col, pct, status, _ in population_report if status == "PARTIAL"]
rare = [col for col, pct, status, _ in population_report if status == "RARE"]
empty = [col for col, pct, status, _ in population_report if status == "EMPTY"]

print(f"\nFULL (>=90%): {len(full)} columns")
for col in full:
    print(f"  - {col}")

print(f"\nPARTIAL (50-90%): {len(partial)} columns")
for col in partial:
    print(f"  - {col}")

print(f"\nRARE (1-50%): {len(rare)} columns")
for col in rare:
    print(f"  - {col}")

print(f"\nEMPTY (0%): {len(empty)} columns")
for col in empty:
    print(f"  - {col}")

conn.close()

print("\n" + "="*80)
print("Audit complete! Review the output above.")
print("="*80)