// import { createStore } from 'vuex';

// export default createStore({
//   state: {
//     user: null,
//   },
//   mutations: {
//     setUser(state, user) {
//       state.user = user;
//     },
//   },
//   actions: {
//     registerUser({ commit }, userData) {
//       // Add registration logic here
//       commit('setUser', userData);
//     },
//   },
//   getters: {
//     isAuthenticated: state => !!state.user,
//   },
// });

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
//   },
//   actions: {
//     login({ commit }, token) {
//       commit('setAccessToken', token);
//     },
//     fetchUserProfile({ commit, state }) {
//       fetch('http://127.0.0.1:8000/profile/me/', {
//         method: 'GET',
//         headers: {
//           'Authorization': `Bearer ${state.accessToken}`,
//           'Accept': 'application/json'
//         }
//       })
//       .then(response => response.json())
//       .then(data => {
//         commit('setUser', data);
//       })
//       .catch(error => console.error('Error fetching profile:', error));
//     }
//   },
//   getters: {
//     isAuthenticated: state => !!state.accessToken,
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
  },
  actions: {
    login({ commit }, token) {
      commit('setAccessToken', token);
    },
    async fetchUserProfile({ commit, state }) {
      try {
        const response = await fetch('http://127.0.0.1:8000/profile/me/', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${state.accessToken}`,
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
    }
  },
  getters: {
    isAuthenticated: state => !!state.accessToken,
    userProfile: state => state.user,
  },
});
