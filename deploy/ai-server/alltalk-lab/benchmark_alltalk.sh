#!/usr/bin/env bash
set -Eeuo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

TTS_SERVICE_URL="${TTS_SERVICE_URL:-http://AI_SERVER_IP:7851}"
ALLTALK_TEST_LANGUAGE="${ALLTALK_TEST_LANGUAGE:-ar}"
ALLTALK_TEST_TEXT="${ALLTALK_TEST_TEXT:-مرحبا، هذا اختبار صوتي آمن لمشروع AI Story Studio.}"
ALLTALK_OUTPUT_NAME="${ALLTALK_OUTPUT_NAME:-ai_story_alltalk_test}"

if [ -z "${ALLTALK_TEST_VOICE:-}" ]; then
  echo "[FAIL] ALLTALK_TEST_VOICE is required. Use only a licensed/owned/safe test voice."
  exit 2
fi

if printf '%s' "$TTS_SERVICE_URL" | grep -q 'AI_SERVER_IP'; then
  echo "[FAIL] Set TTS_SERVICE_URL locally before running. Do not commit real IPs."
  exit 2
fi

echo "[INFO] Checking AllTalk readiness..."
curl -fsS "$TTS_SERVICE_URL/api/ready"
echo

echo "[INFO] Listing available voices..."
curl -fsS "$TTS_SERVICE_URL/api/voices"
echo

echo "[INFO] Requesting TTS generation..."
curl -fsS -X POST "$TTS_SERVICE_URL/api/tts-generate" \
  -F "text_input=$ALLTALK_TEST_TEXT" \
  -F "text_filtering=standard" \
  -F "character_voice_gen=$ALLTALK_TEST_VOICE" \
  -F "narrator_enabled=false" \
  -F "narrator_voice_gen=$ALLTALK_TEST_VOICE" \
  -F "text_not_inside=character" \
  -F "language=$ALLTALK_TEST_LANGUAGE" \
  -F "output_file_name=$ALLTALK_OUTPUT_NAME" \
  -F "output_file_timestamp=true" \
  -F "autoplay=false" \
  -F "autoplay_volume=0.0" \
  -F "streaming=false"
echo

echo "[OK] AllTalk benchmark request completed. Review returned output_file_url/output_file_path."
