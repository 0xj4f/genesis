import { decodeJwtPayload } from '@/utils/jwt';

export const API_BASE = (process.env.VUE_APP_API_URL || 'http://localhost:8001').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// The store registers how to read and refresh tokens, so authenticated calls
// can retry once after a 401 without this module importing the store.
let authHandler = null;
export function setAuthHandler(handler) {
  authHandler = handler;
}

async function send(path, options = {}) {
  const headers = { Accept: 'application/json', ...options.headers };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = res.headers.get('content-type')?.includes('json')
    ? await res.json()
    : null;

  if (!res.ok) {
    const message = data?.detail
      ? (Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail)
      : `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }
  return data;
}

function withBearer(options, token) {
  return { ...options, headers: { ...options.headers, Authorization: `Bearer ${token}` } };
}

// Authenticated request for the 'user' or 'admin' session. On 401 the session
// is refreshed once (shared between concurrent calls) and the call retried.
async function authed(kind, path, options = {}) {
  const token = authHandler?.token(kind);
  try {
    return await send(path, withBearer(options, token));
  } catch (error) {
    if (error.status !== 401 || !authHandler) throw error;
    const freshToken = await authHandler.refresh(kind);
    if (!freshToken) throw error;
    return send(path, withBearer(options, freshToken));
  }
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

const form = fields => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams(fields),
});

const id = value => encodeURIComponent(value);

export default {
  // ---- Auth ----
  login(username, password) {
    return send('/token', form({ username, password }));
  },

  adminLogin(username, password) {
    return send('/admin/login', form({ username, password }));
  },

  refresh(refreshToken) {
    return send('/refresh_token', withBearer({ method: 'POST' }, refreshToken));
  },

  // Revoke the server-side session behind the current access token (logout).
  endSession(kind) {
    const sid = decodeJwtPayload(authHandler?.token(kind) || '')?.sid;
    if (!sid) return Promise.resolve();
    return authed(kind, `/auth/sessions/${id(sid)}`, { method: 'DELETE' });
  },

  getAuthConfig() {
    return send('/auth/config');
  },

  verifyEmail(token) {
    return send('/auth/email/verify', json('POST', { token }));
  },

  resendVerification(email) {
    return send('/auth/email/resend', json('POST', { email }));
  },

  // ---- Users ----
  register(username, email, password) {
    return send('/users/', json('POST', { username, email, password }));
  },

  getMe() {
    return authed('user', '/users/me/');
  },

  updateUser(userId, data) {
    return authed('user', `/users/${id(userId)}`, json('PUT', data));
  },

  changePassword(currentPassword, newPassword) {
    const body = { new_password: newPassword };
    if (currentPassword) body.current_password = currentPassword;
    return authed('user', '/users/me/password', json('POST', body));
  },

  // ---- Profile ----
  getProfile() {
    return authed('user', '/profile/me/');
  },

  createProfile(data) {
    return authed('user', '/profile/', json('POST', data));
  },

  updateProfile(data) {
    return authed('user', '/profile/me/', json('PUT', data));
  },

  uploadPicture(file) {
    const formData = new FormData();
    formData.append('picture', file);
    return authed('user', '/profile/me/picture', { method: 'POST', body: formData });
  },

  deletePicture() {
    return authed('user', '/profile/me/picture', { method: 'DELETE' });
  },

  // ---- Sessions ----
  getSessions() {
    return authed('user', '/auth/sessions');
  },

  revokeSession(sessionId) {
    return authed('user', `/auth/sessions/${id(sessionId)}`, { method: 'DELETE' });
  },

  revokeAllSessions() {
    return authed('user', '/auth/sessions', { method: 'DELETE' });
  },

  // ---- SSO ----
  getSSOProviders() {
    return send('/auth/sso/providers');
  },

  getLinkedProviders() {
    return authed('user', '/auth/sso/linked');
  },

  unlinkProvider(provider) {
    return authed('user', `/auth/sso/${id(provider)}/unlink`, { method: 'DELETE' });
  },

  // Plain navigation target; the API redirects to the provider.
  ssoAuthorizeUrl(provider) {
    return `${API_BASE}/auth/sso/${id(provider)}/authorize`;
  },

  // Credentials are included so the API can set the state cookie that binds
  // the provider round trip to this browser.
  ssoLink(provider) {
    return authed('user', `/auth/sso/${id(provider)}/link`, { method: 'POST', credentials: 'include' });
  },

  // One-time code from the SSO redirect; only works with this browser's cookie.
  ssoExchange(code) {
    return send('/auth/sso/exchange', { ...json('POST', { code }), credentials: 'include' });
  },

  // ---- OAuth consent ----
  getClientInfo(clientId) {
    return send(`/oauth/clients/${id(clientId)}/public`);
  },

  authorizeDecision(params) {
    return authed('user', '/oauth/authorize', json('POST', params));
  },

  // ---- Admin ----
  getAdminMe() {
    return authed('admin', '/users/me/');
  },

  getAnalytics() {
    return authed('admin', '/admin/analytics');
  },

  getAdminUsers(page = 1, perPage = 20, search = '') {
    const params = new URLSearchParams({ page, per_page: perPage });
    if (search) params.set('search', search);
    return authed('admin', `/admin/users?${params}`);
  },

  getAdminUserDetail(userId) {
    return authed('admin', `/admin/users/${id(userId)}`);
  },

  updateUserRole(userId, role) {
    return authed('admin', `/admin/users/${id(userId)}/role`, json('POST', { role }));
  },

  toggleUserStatus(userId) {
    return authed('admin', `/admin/users/${id(userId)}/disable`, { method: 'POST' });
  },

  adminResetPassword(userId, newPassword) {
    return authed('admin', `/admin/users/${id(userId)}/password`, json('POST', { new_password: newPassword }));
  },

  adminDeleteUser(userId) {
    return authed('admin', `/admin/users/${id(userId)}`, { method: 'DELETE' });
  },
};
