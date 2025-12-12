# test_story_insights.py
# Run from project root: python test_story_insights.py

print("=" * 60)
print("TESTING STORY INSIGHTS PAGE")
print("=" * 60)

# Test 1: Import story_card component
print("\n1. Testing story_card component imports...")
try:
    from dashboard.components.story_card import (
        render_story_card,
        render_story_cards_grid,
        render_health_summary,
    )
    print("   ✅ story_card imports successful")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    exit(1)

# Test 2: Import story_insights page
print("\n2. Testing story_insights page imports...")
try:
    from dashboard.pages.story_insights import render_page
    print("   ✅ story_insights imports successful")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    exit(1)

# Test 3: Get story data
print("\n3. Testing story data generation...")
try:
    from dashboard.utils.story_analyzer import get_story_summary
    from dashboard.utils.data_fetcher import get_llm_calls
    
    calls = get_llm_calls(limit=100)
    stories = get_story_summary(calls)
    
    print(f"   ✅ Generated {len(stories)} stories from {len(calls)} calls")
    
    for story in stories:
        status = "🔴" if story['has_issues'] else "🟢"
        print(f"      {status} {story['icon']} {story['title']}: {story['summary_metric']}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Verify story definitions match
print("\n4. Verifying story definitions alignment...")
try:
    from dashboard.config.story_definitions import get_story_definition
    
    all_matched = True
    for story in stories:
        definition = get_story_definition(story['id'])
        if definition:
            if definition['icon'] == story['icon'] and definition['title'] == story['title']:
                print(f"      ✅ {story['id']}: aligned")
            else:
                print(f"      ⚠️ {story['id']}: mismatch")
                all_matched = False
        else:
            print(f"      ❌ {story['id']}: no definition")
            all_matched = False
    
    if all_matched:
        print("   ✅ All stories aligned with definitions")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("STORY INSIGHTS TESTS COMPLETE")
print("=" * 60)
print("\nTo view the dashboard, run:")
print("   streamlit run dashboard/app.py")
print("\nThen navigate to '📊 Story Insights' in the sidebar")