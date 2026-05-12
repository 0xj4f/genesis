<template>
  <div class="analytics-grid">
    <div class="stat-card" v-for="stat in stats" :key="stat.label">
      <div class="stat-value">{{ stat.value }}</div>
      <div class="stat-label">{{ stat.label }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AnalyticsCards',
  props: {
    analytics: { type: Object, default: () => ({}) },
  },
  computed: {
    stats() {
      const a = this.analytics;
      return [
        { label: 'Total Users', value: a.total_users ?? '-' },
        { label: 'Active', value: a.active_users ?? '-' },
        { label: 'Native', value: a.native_count ?? '-' },
        { label: 'SSO', value: a.sso_count ?? '-' },
        { label: 'New (7d)', value: a.new_this_week ?? '-' },
        { label: 'Admins', value: a.admin_count ?? '-' },
      ];
    },
  },
};
</script>

<style scoped>
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--space-md);
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--space-lg) var(--space-md);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent-gradient);
  opacity: 0.4;
}

.stat-value {
  font-family: var(--font-mono);
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--accent);
  text-shadow: 0 0 20px var(--accent-glow);
}

.stat-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: var(--space-xs);
}
</style>
