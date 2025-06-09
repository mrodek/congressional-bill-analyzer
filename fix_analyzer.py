import re
import os
import sys

# Path to the AI analyzer file
analyzer_file = 'src/ai_analyzer.py'

# Read the file content
with open(analyzer_file, 'r') as f:
    content = f.read()

# Replace the problematic regex pattern
fixed_content = content.replace(
    "key_phrases =  re.findall(r'([\\^]+)', content)",
    "key_phrases = re.findall(r\"'([^']+)'\", content)"
)

# Write the fixed content back to the file
with open(analyzer_file, 'w') as f:
    f.write(fixed_content)

print(f"Fixed regex pattern in {analyzer_file}")
