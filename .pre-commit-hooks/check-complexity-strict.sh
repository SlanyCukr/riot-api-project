#!/usr/bin/env bash
# Strict check - only A-grade allowed (complexity <= 5)
# This is a GOAL check, run manually to track progress toward zero complexity > 5

set -e

cd backend
OUTPUT=$(uvx radon cc app/ --min B --show-complexity --no-assert 2>&1)
COUNT=$(echo "$OUTPUT" | grep -c " - [B-F] " || echo 0)

if [ "$COUNT" -gt 0 ]; then
    echo "$OUTPUT"
    echo ""
    echo "Progress: $COUNT functions with B+ grade (complexity >= 6) remaining"
    echo "Long-term goal: Refactor all to A-grade (complexity <= 5)"
    echo "Current standard: complexity <= 7 enforced by default hooks"
    exit 1
fi

echo "SUCCESS! All functions have A-grade complexity (complexity <= 5)"
exit 0
