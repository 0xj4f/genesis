<template>
  <div id="app">
    <nav v-if="isAuthenticated" class="navbar">
      <div class="navbar-inner">
        <router-link to="/profile" class="nav-brand">
          <span class="brand-icon">G</span>
          <span class="brand-text">Genesis</span>
        </router-link>
        <div class="nav-links">
          <router-link to="/profile" class="nav-link">Profile</router-link>
          <router-link to="/sessions" class="nav-link">Sessions</router-link>
          <button class="btn btn-ghost nav-link" @click="logout">Logout</button>
        </div>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'App',
  computed: {
    ...mapGetters(['isAuthenticated']),
  },
  methods: {
    ...mapActions(['logout']),
  },
};
</script>

<style>
/* Load Inter font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.navbar {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-inner {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  text-decoration: none;
  color: var(--text-primary);
  font-weight: 600;
}

.brand-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--accent-gradient);
  color: var(--text-on-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-sm);
}

.brand-text {
  font-size: var(--text-lg);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.nav-link {
  padding: 6px 12px;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.nav-link:hover,
.nav-link.router-link-active {
  color: var(--text-primary);
  background: var(--bg-hover);
}
</style>
