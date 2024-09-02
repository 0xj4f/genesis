// import { createStore } from 'vuex';

// export default createStore({
//   state: {
//     user: null,
//     accessToken: null,
//   },
//   mutations: {
//     setUser(state, user) {
//       state.user = user;
//     },
//     setAccessToken(state, token) {
//       state.accessToken = token;
//     },
//     clearAuthData(state) {
//       state.user = null;
//       state.accessToken = null;
//     }
//   },
//   actions: {
//     login({ commit }, token) {
//       commit('setAccessToken', token);
//     },
//     async fetchUserProfile({ commit, state }) {
//       // Profile fetching logic
//     },
//     logout({ commit }) {
//       commit('clearAuthData');
//       // Additional logic to handle logout (e.g., clearing tokens from local storage)
//     }
//   },
//   getters: {
//     isAuthenticated: state => !!state.accessToken, // Return true if accessToken is not null
//     userProfile: state => state.user,
//   },
// });
import { createStore } from 'vuex';

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
            'Authorization': `Bearer ${this.state.accessToken}`, // Using state directly
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
      // Additional logic to handle logout (e.g., clearing tokens from local storage)
    }
  },
  getters: {
    isAuthenticated: state => !!state.accessToken, // Return true if accessToken is not null
    userProfile: state => state.user,
  },
});
