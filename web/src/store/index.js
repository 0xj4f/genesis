import { createStore } from 'vuex';
import router from '@/router';
import api from '@/api';

export default createStore({
  state: {
    user: null,
    profile: null,
    accessToken: null,
    refreshToken: null,
    ssoProviders: [],
  },

  mutations: {
    setUser(state, user) { state.user = user; },
    setProfile(state, profile) { state.profile = profile; },
    setTokens(state, { accessToken, refreshToken }) {
      state.accessToken = accessToken;
      state.refreshToken = refreshToken || state.refreshToken;
    },
    setSSOProviders(state, providers) { state.ssoProviders = providers; },
    clearAuth(state) {
      state.user = null;
      state.profile = null;
      state.accessToken = null;
      state.refreshToken = null;
    },
  },

  actions: {
    async login({ commit, dispatch }, { username, password }) {
      const data = await api.login(username, password);
      commit('setTokens', { accessToken: data.access_token, refreshToken: data.refresh_token });
      await dispatch('fetchMe');
      await dispatch('fetchProfile');
    },

    handleSSOTokens({ commit, dispatch }, { access_token, refresh_token }) {
      commit('setTokens', { accessToken: access_token, refreshToken: refresh_token });
      dispatch('fetchMe');
      dispatch('fetchProfile');
    },

    async fetchMe({ commit, state }) {
      if (!state.accessToken) return;
      try {
        const user = await api.getMe(state.accessToken);
        commit('setUser', user);
      } catch {
        /* token may be expired */
      }
    },

    async fetchProfile({ commit, state }) {
      if (!state.accessToken) return;
      try {
        const profile = await api.getProfile(state.accessToken);
        commit('setProfile', profile);
      } catch {
        commit('setProfile', null);
      }
    },

    async createProfile({ commit, state }, data) {
      const profile = await api.createProfile(state.accessToken, data);
      commit('setProfile', profile);
      return profile;
    },

    async updateProfile({ commit, state }, data) {
      const profile = await api.updateProfile(state.accessToken, data);
      commit('setProfile', profile);
      return profile;
    },

    async uploadPicture({ commit, state }, file) {
      const result = await api.uploadPicture(state.accessToken, file);
      // Refresh profile to get updated picture URL
      const profile = await api.getProfile(state.accessToken);
      commit('setProfile', profile);
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

    logout({ commit }) {
      commit('clearAuth');
      router.push('/login');
    },
  },

  getters: {
    isAuthenticated: state => !!state.accessToken,
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
