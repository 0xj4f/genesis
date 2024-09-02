import { createStore } from 'vuex';

export default createStore({
  state: {
    user: null,
  },
  mutations: {
    setUser(state, user) {
      state.user = user;
    },
  },
  actions: {
    registerUser({ commit }, userData) {
      // Add registration logic here
      commit('setUser', userData);
    },
  },
  getters: {
    isAuthenticated: state => !!state.user,
  },
});
