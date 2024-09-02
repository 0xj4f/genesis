import { createStore } from 'vuex';
import router from '@/router'; // Import the Vue Router instance

export default createStore({
  state: {
    user: null,
    accessToken: null,
  },
  mutations: {
    setUser(state, user) {
      state.user = user;
    },
    setAccessToken(state, token) {
      state.accessToken = token;
    },
    clearAuthData(state) {
      state.user = null;
      state.accessToken = null;
    }
  },
  actions: {
    login({ commit }, token) {
      commit('setAccessToken', token);
    },
    async fetchUserProfile({ commit }) {
      try {
        const response = await fetch('http://127.0.0.1:8000/profile/me/', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.state.accessToken}`,
            'Accept': 'application/json'
          }
        });
        if (response.ok) {
          const data = await response.json();
          commit('setUser', data);
        } else {
          console.error('Failed to fetch profile data');
        }
      } catch (error) {
        console.error('Error fetching profile:', error);
      }
    },
    logout({ commit }) {
      commit('clearAuthData');
      // Redirect to login page after logout
      router.push('/login');
    }
  },
  getters: {
    isAuthenticated: state => !!state.accessToken, // Return true if accessToken is not null
    userProfile: state => state.user,
  },
});
