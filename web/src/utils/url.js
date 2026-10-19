import { API_BASE } from '@/api';

// Resolve an image URL from the API (relative avatar paths included) and
// allow only http(s), so a stored value can never become a script URL.
export function assetUrl(url) {
  if (!url) return null;
  try {
    const resolved = new URL(url, `${API_BASE}/`);
    return ['http:', 'https:'].includes(resolved.protocol) ? resolved.href : null;
  } catch {
    return null;
  }
}
