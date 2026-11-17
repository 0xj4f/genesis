// OAuth client options shown in the admin console. Mirrors app/models/oauth_client_api_model.py.

export const GRANT_TYPES = [
  { value: 'authorization_code', short: 'Authorization code', label: 'Authorization code',
    hint: 'Users sign in through Genesis and the app receives tokens. Use with PKCE.' },
  { value: 'refresh_token', short: 'Refresh token', label: 'Refresh token',
    hint: 'Keep users signed in without asking again (needs the offline_access scope).' },
  { value: 'client_credentials', short: 'Client credentials', label: 'Client credentials',
    hint: 'Machine-to-machine access with no user. Confidential clients only.', confidentialOnly: true },
];

const LOOPBACK = new Set(['localhost', '127.0.0.1', '[::1]']);

// Same rules as validate_redirect in the API; returns an error message or ''.
export function redirectUriError(value) {
  if (!value) return 'Enter a URL.';
  if (/\s/.test(value) || [...value].some(c => c.charCodeAt(0) < 32)) return 'URLs cannot contain spaces.';
  let url;
  try {
    url = new URL(value);
  } catch {
    return 'Enter a full URL, like https://app.example.com/callback.';
  }
  if (!url.host) return 'The URL needs a host.';
  if (value.includes('#')) return 'Fragments (#…) are not allowed.';
  if (url.username || url.password) return 'Credentials are not allowed in the URL.';
  if (url.protocol === 'https:') return '';
  if (url.protocol === 'http:' && LOOPBACK.has(url.hostname)) return '';
  return 'Use HTTPS. Plain HTTP is allowed only for localhost.';
}
