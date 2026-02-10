#!/usr/bin/env bash
set -euo pipefail

# Recreate the Poetry env and clear Reflex build artifacts.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
  echo "[proj_reinstall] $*"
}

require_python() {
  if ! command -v python3.11 >/dev/null 2>&1; then
    log "python3.11 is required but not found on PATH."
    exit 1
  fi
}

clean_reflex_artifacts() {
  log "Cleaning Reflex build artifacts and caches"
  rm -rf "$ROOT_DIR/.web" "$ROOT_DIR/.states"
  rm -rf "$ROOT_DIR/assets/external"
  find "$ROOT_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
  find "$ROOT_DIR" -maxdepth 1 -name "*.db" -type f -delete
}

clean_uploads() {
  log "Removing uploaded files"
  rm -rf "$ROOT_DIR/uploaded_files"
}

remove_poetry_envs() {
  log "Removing existing Poetry environments for this project"
  local envs
  envs=$(cd "$ROOT_DIR" && poetry env list --full-path 2>/dev/null || true)
  if [[ -z "${envs// /}" ]]; then
    log "No existing Poetry environments found"
    return
  fi

  # Track removal outcomes for a final summary.
  local removed_envs=()
  local failed_envs=()

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    # Trim the status suffix like "(Activated)" if present.
    local env_path
    env_path="${line%% *}"
    local env_name
    env_name="${env_path##*/}"
    # Skip envs we cannot write to (avoids breaking on permission errors).
    if [[ ! -w "$env_path" ]]; then
      log "Skipping env at $env_path (not writable)"
      continue
    fi

    log "Removing env $env_name"
    if ! (cd "$ROOT_DIR" && poetry env remove "$env_name"); then
      log "Failed to remove $env_name, continuing"
      failed_envs+=("$env_path")
      continue
    fi
    removed_envs+=("$env_path")
  done <<< "$envs"

  if (( ${#removed_envs[@]} )); then
    log "Removed envs: ${removed_envs[*]}"
  else
    log "No envs removed"
  fi

  if (( ${#failed_envs[@]} )); then
    log "Failed to remove envs: ${failed_envs[*]}"
  else
    log "No removal failures"
  fi
}

recreate_poetry_env() {
  log "Creating Poetry environment with python3.11"
  (cd "$ROOT_DIR" && poetry env use python3.11)
  log "Installing dependencies"
  (cd "$ROOT_DIR" && poetry install)
}

main() {
  require_python
  clean_reflex_artifacts
  clean_uploads
  remove_poetry_envs
  recreate_poetry_env
  log "Done"
}

main "$@"