#!/bin/sh

# Install jq
echo "📦 Installing jq..."
apk add --no-cache jq

# Run GitLab secret detection analyzer https://gitlab.com/gitlab-org/gitlab/-/tree/master/lib/gitlab/ci/reports/security
/analyzer run

# Copy base JSON (standard GitLab analyzer findings)
cp gl-secret-detection-report.json gl-secret-detection-report.merged.json

# --- Collect customized token findings using regular expressions (Overleaf token prefixed) ---
grep -R -nE 'olp_[A-Za-z0-9_]+' . | grep -v '^\./\.git/' > /tmp/overleaf_findings.txt 2>/dev/null || true

if [ -s /tmp/overleaf_findings.txt ]; then
  while IFS=: read -r file line content; do
    jq --arg file "$file" \
       --arg line "$line" \
       --arg content "$content" \
       '.vulnerabilities += [{
          "id":"overleaf_token",
          "category":"custom",
          "file":$file,
          "line":($line|tonumber),
          "name":"Overleaf token",
          "raw_source_code_extract":$content
        }]' gl-secret-detection-report.merged.json > tmp.json \
        && mv tmp.json gl-secret-detection-report.merged.json
  done < /tmp/overleaf_findings.txt
fi

# --- Collect customized domain secrets using regular expressions (Espressif / SharePoint) ---
grep -R -nE '\.(espressif\.(com|cn)\:|sharepoint\.com)' . \
  | grep -v '^\./\.git/' > /tmp/domain_findings.txt 2>/dev/null || true

if [ -s /tmp/domain_findings.txt ]; then
  while IFS=: read -r file line content; do
    jq --arg file "$file" \
       --arg line "$line" \
       --arg content "$content" \
       '.vulnerabilities += [{
          "id":"secret_domain",
          "category":"custom",
          "file":$file,
          "line":($line|tonumber),
          "name":"Espressif domain",
          "raw_source_code_extract":$content
        }]' gl-secret-detection-report.merged.json > tmp.json \
        && mv tmp.json gl-secret-detection-report.merged.json
  done < /tmp/domain_findings.txt
fi

# --- Count total vulnerabilities ---
NUMBER_OF_TOTAL=$(jq --raw-output '.vulnerabilities | length' gl-secret-detection-report.merged.json)

# --- Print results and fail if necessary ---
if [ "$NUMBER_OF_TOTAL" -gt 0 ]; then
  echo "❌ Detected $NUMBER_OF_TOTAL secret(s)."
  jq -r '
    .vulnerabilities[] |
    if has("location") then
      " ⚠️ \(.name) \(.raw_source_code_extract) found in \(.location.file) line \(.location.start_line)"
    else
      " ⚠️ \(.name) \(.raw_source_code_extract) found in \(.file) line \(.line)"
    end
  ' gl-secret-detection-report.merged.json
  exit 1
else
  echo "✅ No secrets found"
fi
