// Read (not verify) a JWT payload. The API verifies tokens; the web app only
// needs the expiry and session id for its own bookkeeping.
export function decodeJwtPayload(token) {
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = part + '='.repeat((4 - (part.length % 4)) % 4);
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

export function isExpired(token, skewSeconds = 10) {
  const payload = token && decodeJwtPayload(token);
  if (!payload || !payload.exp) return true;
  return payload.exp - skewSeconds <= Date.now() / 1000;
}
