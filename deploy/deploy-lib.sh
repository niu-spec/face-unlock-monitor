#!/usr/bin/env bash
# Shared helpers for production deploy scripts (manual SSH + Jenkins CD).

deploy_use_sudo() {
  case "${DEPLOY_USE_SUDO:-auto}" in
    1 | true | yes) return 0 ;;
    0 | false | no) return 1 ;;
    auto) [ "$(id -u)" -ne 0 ] ;;
    *) return 1 ;;
  esac
}

# Run a command with passwordless sudo when DEPLOY_USE_SUDO=auto|1 and not root.
deploy_privileged() {
  if deploy_use_sudo && command -v sudo >/dev/null 2>&1; then
    sudo -n "$@"
  else
    "$@"
  fi
}

deploy_systemctl() {
  if ! command -v systemctl >/dev/null 2>&1; then
    return 1
  fi
  deploy_privileged systemctl "$@"
}

deploy_nginx() {
  if ! command -v nginx >/dev/null 2>&1; then
    return 1
  fi
  deploy_privileged nginx "$@"
}
