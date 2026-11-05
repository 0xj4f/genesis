<template>
  <div class="admin-shell">
    <!-- Sidebar (>= 1024px) -->
    <aside class="sidebar" aria-label="Admin">
      <router-link to="/admin" class="brand sidebar-brand">
        <BrandMark />
        <span>Genesis</span>
        <span class="badge badge-warning">Admin</span>
      </router-link>
      <nav class="sidebar-nav" aria-label="Admin sections">
        <router-link v-for="item in nav" :key="item.to" :to="item.to" class="sidebar-link"
                     :class="{ 'is-active': isActive(item) }" :aria-current="isActive(item) ? 'page' : undefined">
          <component :is="item.icon" :size="18" aria-hidden="true" />{{ item.label }}
        </router-link>
      </nav>
      <div class="sidebar-foot">
        <div class="row sidebar-account">
          <span class="avatar avatar-sm avatar-placeholder">{{ initials }}</span>
          <div class="wrap-anywhere">
            <div class="text-md truncate"><strong>{{ adminName }}</strong></div>
            <div class="text-sm text-muted">{{ roleLabel }}</div>
          </div>
        </div>
        <ThemeToggle />
        <button class="btn btn-ghost btn-sm sidebar-signout" @click="adminLogout">
          <LogOut :size="16" aria-hidden="true" />Sign out
        </button>
      </div>
    </aside>

    <!-- Top bar (< 1024px) -->
    <header class="topbar admin-topbar">
      <div class="topbar-inner">
        <router-link to="/admin" class="brand">
          <BrandMark />
          <span>Genesis</span>
          <span class="badge badge-warning">Admin</span>
        </router-link>
        <div class="spacer"></div>
        <AccountMenu :name="adminName" :email="adminUser?.email" :initials="initials" @sign-out="adminLogout" />
      </div>
    </header>

    <main class="admin-main">
      <router-view />
    </main>

    <nav class="tabbar admin-tabbar" aria-label="Admin sections">
      <router-link v-for="item in nav" :key="item.to" :to="item.to" :class="{ 'is-active': isActive(item) }"
                   :aria-current="isActive(item) ? 'page' : undefined">
        <component :is="item.icon" :size="22" aria-hidden="true" />{{ item.short || item.label }}
      </router-link>
    </nav>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { LayoutDashboard, Users, AppWindow, LogOut } from 'lucide-vue-next';
import BrandMark from '@/components/ui/BrandMark.vue';
import AccountMenu from '@/components/ui/AccountMenu.vue';
import ThemeToggle from '@/components/ui/ThemeToggle.vue';

export default {
  name: 'AdminLayout',
  components: { LogOut, BrandMark, AccountMenu, ThemeToggle },
  data() {
    return {
      nav: [
        { to: '/admin', label: 'Overview', icon: LayoutDashboard, exact: true },
        { to: '/admin/users', label: 'Users', icon: Users },
        { to: '/admin/applications', label: 'Applications', short: 'Apps', icon: AppWindow },
      ],
    };
  },
  computed: {
    ...mapState(['adminUser']),
    adminName() { return this.adminUser?.username || 'Administrator'; },
    initials() { return (this.adminUser?.username?.[0] || 'A').toUpperCase(); },
    roleLabel() { return this.adminUser?.role === 'root' ? 'Root administrator' : 'Administrator'; },
  },
  methods: {
    ...mapActions(['adminLogout']),
    isActive(item) {
      const path = this.$route.path;
      return item.exact ? path === item.to || path === `${item.to}/` : path.startsWith(item.to);
    },
  },
};
</script>

<style scoped>
.admin-shell {
  min-height: 100vh;
  min-height: 100dvh;
  padding-bottom: calc(var(--tabbar-h) + var(--safe-bottom));
}

.sidebar { display: none; }

/* Tab bar is shown below 1024px here (wider than the user app's 768px). */
.admin-tabbar { display: flex; }
.admin-tabbar a.router-link-active:not(.is-active) { color: var(--text-subtle); }

.admin-main { min-width: 0; }

@media (min-width: 1024px) {
  .admin-shell {
    display: grid;
    grid-template-columns: 248px minmax(0, 1fr);
    padding-bottom: 0;
  }

  .admin-topbar, .admin-tabbar { display: none; }

  .sidebar {
    display: flex;
    flex-direction: column;
    position: sticky;
    top: 0;
    height: 100vh;
    height: 100dvh;
    padding: var(--space-md) var(--space-sm);
    border-right: 1px solid var(--border);
    background: var(--surface);
  }
}

.sidebar-brand { padding: var(--space-xs) var(--space-sm) var(--space-lg); }
.sidebar-nav { display: flex; flex-direction: column; gap: 2px; }

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 10px;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  text-decoration: none;
  font-size: var(--text-md);
  font-weight: 500;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.sidebar-link:hover { background: var(--surface-hover); color: var(--text); }
.sidebar-link.is-active { background: var(--surface-2); color: var(--text); }
.sidebar-link.is-active svg { color: var(--primary-text); }

.sidebar-foot {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-sm) 0;
  border-top: 1px solid var(--border);
}

.sidebar-account { gap: 10px; }
.sidebar-signout { justify-content: flex-start; padding: 0 6px; }
</style>
