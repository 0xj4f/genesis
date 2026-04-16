const API_BASE = process.env.VUE_APP_API_URL || 'http://localhost:8001';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = { Accept: 'application/json', ...options.headers };

  const res = await fetch(url, { ...options, headers });
  const data = res.headers.get('content-type')?.includes('json')
    ? await res.json()
    : null;

  if (!res.ok) {
    const message = data?.detail
      ? (Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail)
      : `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}

export default {
  // Auth
  login(username, password) {
    const body = new URLSearchParams({ username, password });
    return request('/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
  },

  refreshToken(refreshToken) {
    return request('/refresh_token', {
      method: 'POST',
      headers: authHeaders(refreshToken),
    });
  },

  // Users
  register(username, email, password) {
    return request('/users/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
  },

  getMe(token) {
    return request('/users/me/', { headers: authHeaders(token) });
  },

  // Profile
  getProfile(token) {
    return request('/profile/me/', { headers: authHeaders(token) });
  },

  createProfile(token, data) {
    return request('/profile/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify(data),
    });
  },

  updateProfile(token, data) {
    return request('/profile/me/', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify(data),
    });
  },

  uploadPicture(token, file) {
    const formData = new FormData();
    formData.append('picture', file);
    return request('/profile/me/picture', {
      method: 'POST',
      headers: authHeaders(token),
      body: formData,
    });
  },

  deletePicture(token) {
    return request('/profile/me/picture', {
      method: 'DELETE',
      headers: authHeaders(token),
    });
  },

  // Sessions
  getSessions(token) {
    return request('/auth/sessions', { headers: authHeaders(token) });
  },

  revokeSession(token, sessionId) {
    return request(`/auth/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
  },

  revokeAllSessions(token) {
    return request('/auth/sessions', {
      method: 'DELETE',
      headers: authHeaders(token),
    });
  },

  // SSO
  getSSOProviders() {
    return request('/auth/sso/providers');
  },

  getLinkedProviders(token) {
    return request('/auth/sso/linked', { headers: authHeaders(token) });
  },

  unlinkProvider(token, provider) {
    return request(`/auth/sso/${provider}/unlink`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
  },

  // Returns the redirect URL (caller opens it)
  ssoAuthorizeUrl(provider) {
    return `${API_BASE}/auth/sso/${provider}/authorize`;
  },

  ssoLinkUrl(provider) {
    return `${API_BASE}/auth/sso/${provider}/link`;
  },

  // Admin
  adminLogin(username, password) {
    const body = new URLSearchParams({ username, password });
    return request('/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
  },

  getAnalytics(token) {
    return request('/admin/analytics', { headers: authHeaders(token) });
  },

  getAdminUsers(token, page = 1, perPage = 20, search = '') {
    const params = new URLSearchParams({ page, per_page: perPage });
    if (search) params.set('search', search);
    return request(`/admin/users?${params}`, { headers: authHeaders(token) });
  },

  getAdminUserDetail(token, userId) {
    return request(`/admin/users/${userId}`, { headers: authHeaders(token) });
  },

  updateUserRole(token, userId, role) {
    return request(`/admin/users/${userId}/role`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ role }),
    });
  },

  toggleUserStatus(token, userId) {
    return request(`/admin/users/${userId}/disable`, {
      method: 'POST',
      headers: authHeaders(token),
    });
  },

  adminDeleteUser(token, userId) {
    return request(`/admin/users/${userId}`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
  },
};
