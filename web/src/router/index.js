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
    meta: { bare: true },
  },
  {
    path: '/verify-email',
    name: 'VerifyEmail',
    component: () => import('@/views/VerifyEmailView.vue'),
    meta: { bare: true },
  },
  {
    // Browser-facing OAuth authorize step: sign in, then consent.
    path: '/oauth/authorize',
    name: 'OAuthConsent',
    component: () => import('@/views/ConsentView.vue'),
    meta: { requiresAuth: true, bare: true },
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
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/DashboardView.vue'),
      },
      {
        // The open user lives in the URL, so back (or the iOS swipe) closes it.
        path: 'users/:id?',
        name: 'AdminUsers',
        component: () => import('@/views/admin/UsersView.vue'),
      },
      {
        path: 'applications',
        name: 'AdminApplications',
        component: () => import('@/views/admin/ApplicationsView.vue'),
      },
      {
        path: 'applications/new',
        name: 'AdminApplicationNew',
        component: () => import('@/views/admin/ApplicationFormView.vue'),
      },
      {
        path: 'applications/:id',
        name: 'AdminApplication',
        component: () => import('@/views/admin/ApplicationFormView.vue'),
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved;
    // Opening or closing a user keeps the list where it was.
    if (to.name === from.name && to.name === 'AdminUsers') return false;
    return { top: 0 };
  },
});

// These checks only decide what to show; the API authorizes every request.
router.beforeEach((to, from, next) => {
  const isAuth = store.getters.isAuthenticated;
  const isAdmin = store.getters.isAdminAuthenticated;

  if (to.meta.requiresAuth && !isAuth) {
    return next({ path: '/login', query: { next: to.fullPath } });
  }
  if (to.meta.guest && isAuth) {
    return next('/profile');
  }
  if (to.matched.some(record => record.meta.requiresAdmin) && !isAdmin) {
    return next(to.path === '/admin' ? '/admin/login' : { path: '/admin/login', query: { next: to.fullPath } });
  }
  if (to.meta.adminGuest && isAdmin) {
    return next('/admin');
  }
  next();
});

export default router;
