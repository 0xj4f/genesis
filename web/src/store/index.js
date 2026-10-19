import { createStore } from 'vuex';
import router from '@/router';
import api, { setAuthHandler } from '@/api';
import { isExpired } from '@/utils/jwt';

// Tokens live in memory only (never localStorage), which keeps them away from
// other scripts on the origin but means a page reload signs the user out.
const store = createStore({
  state: {
    user: null,
    profile: null,
    accessToken: null,
    refreshToken: null,
    ssoProviders: [],
    authConfig: { email_verification: false },
    adminToken: null,
    adminRefreshToken: null,
    adminUser: null,
  },

  mutations: {
    setUser(state, user) { state.user = user; },
    setProfile(state, profile) { state.profile = profile; },
    setTokens(state, { accessToken, refreshToken }) {
      state.accessToken = accessToken;
      state.refreshToken = refreshToken || state.refreshToken;
    },
    setSSOProviders(state, providers) { state.ssoProviders = providers; },
    setAuthConfig(state, config) { state.authConfig = config; },
    setAdminTokens(state, { accessToken, refreshToken }) {
      state.adminToken = accessToken;
      state.adminRefreshToken = refreshToken || state.adminRefreshToken;
    },
    setAdminUser(state, user) { state.adminUser = user; },
    clearAuth(state) {
      state.user = null;
      state.profile = null;
      state.accessToken = null;
      state.refreshToken = null;
    },
    clearAdminAuth(state) {
      state.adminToken = null;
      state.adminRefreshToken = null;
      state.adminUser = null;
    },
  },

  actions: {
    async login({ dispatch }, { username, password }) {
      const data = await api.login(username, password);
      await dispatch('completeLogin', data);
    },

    // Shared by password login and the SSO hand-off.
    async completeLogin({ commit, dispatch }, { access_token, refresh_token }) {
      commit('setTokens', { accessToken: access_token, refreshToken: refresh_token });
      await Promise.all([dispatch('fetchMe'), dispatch('fetchProfile')]);
    },

    // Returns the new access token, or null after signing the session out.
    async refreshSession({ state, commit }, kind) {
      const admin = kind === 'admin';
      const refreshToken = admin ? state.adminRefreshToken : state.refreshToken;
      if (refreshToken) {
        try {
          const data = await api.refresh(refreshToken);
          const tokens = { accessToken: data.access_token, refreshToken: data.refresh_token };
          commit(admin ? 'setAdminTokens' : 'setTokens', tokens);
          return data.access_token;
        } catch {
          /* fall through: the session is gone */
        }
      }
      commit(admin ? 'clearAdminAuth' : 'clearAuth');
      router.push(admin ? '/admin/login' : '/login');
      return null;
    },

    async fetchMe({ commit, state }) {
      if (!state.accessToken) return;
      try {
        commit('setUser', await api.getMe());
      } catch {
        /* signed out or unavailable */
      }
    },

    async fetchProfile({ commit, state }) {
      if (!state.accessToken) return;
      try {
        commit('setProfile', await api.getProfile());
      } catch {
        commit('setProfile', null);
      }
    },

    async createProfile({ commit }, data) {
      const profile = await api.createProfile(data);
      commit('setProfile', profile);
      return profile;
    },

    async updateProfile({ commit }, data) {
      const profile = await api.updateProfile(data);
      commit('setProfile', profile);
      return profile;
    },

    async uploadPicture({ commit }, file) {
      const result = await api.uploadPicture(file);
      commit('setProfile', await api.getProfile());
      return result;
    },

    async fetchSSOProviders({ commit }) {
      try {
        const data = await api.getSSOProviders();
        commit('setSSOProviders', data.providers || []);
      } catch {
        commit('setSSOProviders', []);
      }
    },

    async fetchAuthConfig({ commit }) {
      try {
        commit('setAuthConfig', await api.getAuthConfig());
      } catch {
        /* keep defaults */
      }
    },

    async adminLogin({ commit }, { username, password }) {
      const data = await api.adminLogin(username, password);
      commit('setAdminTokens', { accessToken: data.access_token, refreshToken: data.refresh_token });
      try {
        commit('setAdminUser', await api.getAdminMe());
      } catch {
        /* role-dependent controls stay hidden */
      }
    },

    // Logout ends the session on the server too, so its refresh token stops working.
    async adminLogout({ commit, state }) {
      if (state.adminToken) {
        try { await api.endSession('admin'); } catch { /* already gone */ }
      }
      commit('clearAdminAuth');
      router.push('/admin/login');
    },

    async logout({ commit, state }) {
      if (state.accessToken) {
        try { await api.endSession('user'); } catch { /* already gone */ }
      }
      commit('clearAuth');
      router.push('/login');
    },
  },

  getters: {
    // An expired access token still counts while a refresh token can renew it.
    isAuthenticated: state => !!state.accessToken && (!!state.refreshToken || !isExpired(state.accessToken)),
    isAdminAuthenticated: state => !!state.adminToken && (!!state.adminRefreshToken || !isExpired(state.adminToken)),
    isRootAdmin: state => state.adminUser?.role === 'root',
    userProfile: state => state.profile,
    hasProfile: state => !!state.profile,
    currentUser: state => state.user,
    initials: state => {
      if (state.profile) {
        const g = state.profile.given_name?.[0] || '';
        const f = state.profile.family_name?.[0] || '';
        return (g + f).toUpperCase() || '?';
      }
      if (state.user) return state.user.username?.[0]?.toUpperCase() || '?';
      return '?';
    },
  },
});

// One refresh at a time per session; concurrent 401s wait for the same result.
const refreshing = {};
setAuthHandler({
  token: kind => (kind === 'admin' ? store.state.adminToken : store.state.accessToken),
  refresh(kind) {
    if (!refreshing[kind]) {
      refreshing[kind] = store.dispatch('refreshSession', kind).finally(() => { refreshing[kind] = null; });
    }
    return refreshing[kind];
  },
});

export default store;
