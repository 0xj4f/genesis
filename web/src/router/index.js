import { createRouter, createWebHistory } from 'vue-router'
import store from '@/store'; // Import the Vuex store
import HomeView from '../views/HomeView.vue'
import RegistrationView from '@/views/RegistrationView.vue'; 
import LoginView from '@/views/LoginView.vue'; 
import ProfileView from '@/views/ProfileView.vue'; // Import the profile view


const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/about',
    name: 'about',
    // route level code-splitting
    // this generates a separate chunk (about.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    component: () => import(/* webpackChunkName: "about" */ '../views/AboutView.vue')
  },
    {
    path: '/register',
    name: 'Register',
    component: RegistrationView,
  },
    {
    path: '/login',
    name: 'Login',
    component: LoginView,
  },
  {
    path: '/profile',
    name: 'Profile',
    component: ProfileView,
    meta: { requiresAuth: true }, // Meta field to indicate that this route requires authentication

  },



]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})


// Navigation Guard
router.beforeEach((to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!store.getters.isAuthenticated) {
      next('/login'); // Redirect to login page if not authenticated
    } else {
      next(); // Allow access if authenticated
    }
  } else {
    next(); // Allow access if the route does not require authentication
  }
});

export default router
