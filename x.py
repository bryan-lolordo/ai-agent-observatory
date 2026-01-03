#!/usr/bin/env python3
"""
Add PageContainer to files - opening tag only.
User will manually close the tags.

Usage:
    python add_pagecontainer.py path/to/file1.jsx path/to/file2.jsx
"""

import re
import sys
from pathlib import Path


def count_parent_dirs(file_path):
    """Count how many '../' needed to reach src/components from file"""
    parts = Path(file_path).parts
    if 'src' in parts:
        src_index = parts.index('src')
        depth = len(parts) - src_index - 1
        return '../' * depth + 'components/layout/PageContainer'
    return '../../../components/layout/PageContainer'


def add_page_container_import(content, file_path):
    """Add PageContainer import if not present"""
    if 'import PageContainer' in content:
        print("  ℹ️  Import already exists")
        return content, False
    
    # Determine correct import path
    import_path = count_parent_dirs(file_path)
    import_line = f"import PageContainer from '{import_path}';"
    
    # Find last import statement
    lines = content.split('\n')
    last_import_index = -1
    
    for i, line in enumerate(lines):
        if line.strip().startswith('import '):
            last_import_index = i
    
    if last_import_index >= 0:
        lines.insert(last_import_index + 1, import_line)
        print(f"  ✅ Added import: {import_line}")
        return '\n'.join(lines), True
    
    print("  ⚠️  Could not find import location")
    return content, False


def replace_max_width_divs(content):
    """Replace max-w-7xl divs with PageContainer"""
    # Pattern matches: <div className="max-w-7xl mx-auto p-6">
    # And variations
    patterns = [
        r'<div className="max-w-7xl mx-auto p-6">',
        r'<div className="max-w-7xl mx-auto p-8">',
        r'<div className="max-w-7xl mx-auto p-4">',
        r'<div className=["\']max-w-7xl mx-auto p-\d+["\']>',
    ]
    
    replaced = False
    for pattern in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, '<PageContainer>', content)
            replaced = True
            print(f"  ✅ Replaced opening div with <PageContainer>")
    
    if not replaced:
        print("  ℹ️  No max-w-7xl divs found")
    else:
        print("  ⚠️  YOU MUST manually change the matching </div> to </PageContainer>")
    
    return content, replaced


def update_file(file_path):
    """Update a single file"""
    print(f"\n📄 Processing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add import
        content, import_added = add_page_container_import(content, file_path)
        
        # Replace divs
        content, divs_replaced = replace_max_width_divs(content)
        
        # Write if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, "Updated - MANUALLY CLOSE </PageContainer>" if divs_replaced else "Import added"
        else:
            return False, "No changes needed"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_pagecontainer.py <file1.jsx> <file2.jsx> ...")
        print("\nThis script will:")
        print("  1. Add PageContainer import")
        print("  2. Replace <div className='max-w-7xl mx-auto p-6'> with <PageContainer>")
        print("  3. YOU manually change the matching </div> to </PageContainer>")
        sys.exit(1)
    
    files = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(path.rglob('*.jsx'))
            files.extend(path.rglob('*.js'))
    
    if not files:
        print("No files found to process")
        sys.exit(1)
    
    print(f"🚀 Processing {len(files)} files...")
    print("="*60)
    
    updated = 0
    skipped = 0
    errors = 0
    
    for file_path in files:
        changed, message = update_file(file_path)
        
        if changed:
            print(f"✅ {message}")
            updated += 1
        elif "Error" in message:
            print(f"❌ {message}")
            errors += 1
        else:
            print(f"⏭️  {message}")
            skipped += 1
    
    print("\n" + "="*60)
    print(f"Summary:")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")
    
    if updated > 0:
        print("\n⚠️  IMPORTANT: Search for <PageContainer> in your files")
        print("   and manually change the matching </div> to </PageContainer>")
    print("="*60)


if __name__ == '__main__':
    main()