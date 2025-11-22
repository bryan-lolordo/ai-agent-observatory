from observatory import Storage

storage = Storage()

# Check what's in the database
sessions = storage.get_sessions(limit=100)
print(f'📊 Total sessions in DB: {len(sessions)}')
print()

# Group by project
from collections import defaultdict
by_project = defaultdict(list)
for s in sessions:
    by_project[s.project_name].append(s)

print("Sessions by project:")
for project, project_sessions in by_project.items():
    print(f'\n  📁 {project}: {len(project_sessions)} sessions')
    for s in project_sessions[:5]:  # Show first 5 of each project
        print(f'     • {s.operation_type or "N/A"} | ${s.total_cost:.4f} | {s.start_time}')