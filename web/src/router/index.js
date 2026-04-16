import { createRouter, createWebHistory } from 'vue-router';
import store from '@/store';

const routes = [
  {
    path: '/',
    redirect: () => (store.getters.isAuthenticated ? '/profile' : '/login'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/sso/callback',
    name: 'SSOCallback',
    component: () => import('@/views/SSOCallbackView.vue'),
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/profile/create',
    name: 'CreateProfile',
    component: () => import('@/views/CreateProfileView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/sessions',
    name: 'Sessions',
    component: () => import('@/views/SessionsView.vue'),
    meta: { requiresAuth: true },
  },

  // ---- Admin Routes ----
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('@/views/AdminLoginView.vue'),
    meta: { adminGuest: true },
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/DashboardView.vue'),
    meta: { requiresAdmin: true },
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

router.beforeEach((to, from, next) => {
  const isAuth = store.getters.isAuthenticated;
  const isAdmin = store.getters.isAdminAuthenticated;

  if (to.meta.requiresAuth && !isAuth) {
    return next('/login');
  }
  if (to.meta.guest && isAuth) {
    return next('/profile');
  }
  if (to.meta.requiresAdmin && !isAdmin) {
    return next('/admin/login');
  }
  if (to.meta.adminGuest && isAdmin) {
    return next('/admin');
  }
  next();
});

export default router;
