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

deploy_nginx_bin() {
  if [ -n "${NGINX_BIN:-}" ] && [ -x "${NGINX_BIN}" ]; then
    echo "${NGINX_BIN}"
    return 0
  fi
  local candidate
  for candidate in \
    "$(command -v nginx 2>/dev/null || true)" \
    /usr/bin/nginx \
    /usr/sbin/nginx \
    /www/server/nginx/sbin/nginx; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

deploy_nginx() {
  local bin
  bin="$(deploy_nginx_bin)" || return 1
  deploy_privileged "$bin" "$@"
}

deploy_nginx_reload() {
  if command -v systemctl >/dev/null 2>&1 && deploy_systemctl is-active --quiet nginx 2>/dev/null; then
    deploy_systemctl reload nginx
    return 0
  fi
  if [ -x /etc/init.d/nginx ]; then
    deploy_privileged /etc/init.d/nginx reload
    return 0
  fi
  deploy_nginx -s reload
}
