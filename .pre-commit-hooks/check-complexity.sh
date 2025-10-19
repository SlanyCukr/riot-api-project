#!/usr/bin/env bash
# Check cyclomatic complexity - blocks complexity >= 8 (allows A-grade + simple B-grade)
set -e

cd backend
OUTPUT=$(uvx radon cc app/ --min B --show-complexity --no-assert 2>&1)

# Check for complexity 8 or higher (C-F grades or high B: 8, 9, 10)
if echo "$OUTPUT" | grep -qE " - (B \([89]|B \(10\)|[C-F] \()"; then
    echo "$OUTPUT"
    echo ""
    echo "ERROR: Code complexity too high!"
    echo "Found functions with complexity >= 8."
    echo "Allowed: A-grade (1-5) and simple B-grade (6-7)."
    echo "Please refactor functions with complexity >= 8 to keep code maintainable."
    exit 1
fi

echo "✓ All functions have acceptable complexity (<= 7)"
exit 0
