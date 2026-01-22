#!/bin/bash
# generate_preview_content.sh

OUTPUT_FILE="preview_posts.md"

echo "# 貼文預覽 (Local Preview)" > "$OUTPUT_FILE"
echo "Generated at: $(date)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "## 📡 獨立音樂雷達 (Radar Events)" >> "$OUTPUT_FILE"
echo "\`\`\`text" >> "$OUTPUT_FILE"
./venv/bin/python post_radar_to_threads.py --dry-run >> "$OUTPUT_FILE" 2>&1
echo "\`\`\`" >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"
echo "## 🎹 官方售票活動 (Official Events)" >> "$OUTPUT_FILE"
echo "\`\`\`text" >> "$OUTPUT_FILE"
./venv/bin/python post_official_to_threads.py --dry-run >> "$OUTPUT_FILE" 2>&1
echo "\`\`\`" >> "$OUTPUT_FILE"

echo "✅ Preview generated in $OUTPUT_FILE"
