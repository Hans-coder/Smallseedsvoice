#!/bin/bash
# verify_local_run.sh
# Script to verify the scraper -> preview workflow locally

echo "🔍 Starting local verification..."

# 1. Run Data Scraper
echo "\n📌 Step 1: Running Activity Radar Scraper..."
./venv/bin/python scrape_activity_radar.py

if [ $? -eq 0 ]; then
    echo "✅ Scraper finished successfully."
else
    echo "❌ Scraper failed. Check logs."
    exit 1
fi

# 2. Run Preview Generator
echo "\n📌 Step 2: Generating Preview..."
./venv/bin/python preview_generator.py

if [ $? -eq 0 ]; then
    echo "✅ Preview generated. Check preview.html"
else
    echo "❌ Preview generation failed."
    exit 1
fi

echo "\n🎉 Verification Complete! Open 'preview.html' to check results."
