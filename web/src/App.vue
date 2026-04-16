<template>
  <div id="app">
    <nav v-if="isAuthenticated" class="navbar">
      <div class="navbar-inner">
        <router-link to="/profile" class="nav-brand">
          <span class="brand-icon">&gt;_</span>
          <span class="brand-text">genesis<span class="text-accent">_iam</span></span>
        </router-link>
        <div class="nav-links">
          <router-link to="/profile" class="nav-link">// profile</router-link>
          <router-link to="/sessions" class="nav-link">// sessions</router-link>
          <button class="btn btn-ghost nav-link" @click="logout">// logout</button>
        </div>
      </div>
    </nav>
    <router-view />
    <footer v-if="!isAuthenticated" class="auth-footer">
      <span class="text-muted">built by </span><span class="text-accent">0xj4f</span>
    </footer>
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
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

.navbar {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.3;
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
  font-family: var(--font-mono);
  font-weight: 600;
}

.brand-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  border: 1px solid var(--border-accent);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}

.brand-text {
  font-size: var(--text-base);
  font-family: var(--font-mono);
}

.text-accent {
  color: var(--accent);
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
  font-family: var(--font-mono);
  color: var(--text-muted);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.nav-link:hover,
.nav-link.router-link-active {
  color: var(--accent);
  background: var(--accent-glow);
}

.auth-footer {
  position: fixed;
  bottom: var(--space-lg);
  left: 50%;
  transform: translateX(-50%);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.05em;
}
</style>
