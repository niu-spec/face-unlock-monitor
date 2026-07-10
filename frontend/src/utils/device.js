export function isMobileDevice() {
  if (typeof navigator === 'undefined') return false
  return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)
}

export function getPublicBaseUrl() {
  const configured = import.meta.env.VITE_PUBLIC_BASE_URL
  if (configured) return String(configured).replace(/\/$/, '')
  if (typeof window !== 'undefined') return window.location.origin
  return ''
}
