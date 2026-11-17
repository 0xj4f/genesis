<template>
  <div class="page-container admin-page">
    <div class="page-header">
      <div>
        <h1>Overview</h1>
        <p>Identity activity across your Genesis tenant</p>
      </div>
      <router-link to="/admin/users" class="btn btn-secondary btn-sm">
        <Users :size="16" aria-hidden="true" />Manage users
      </router-link>
    </div>

    <ErrorAlert v-if="error" :message="error" class="mb-md" @retry="load" />

    <router-link v-if="counts.open" to="/admin/requests" class="alert alert-warning requests-banner">
      <Inbox :size="18" aria-hidden="true" />
      <span class="spacer">
        <strong>{{ counts.open }} {{ counts.open === 1 ? 'person is' : 'people are' }} waiting for a password reset</strong>
      </span>
      <span class="text-md">Review</span><ChevronRight :size="16" aria-hidden="true" />
    </router-link>

    <!-- KPIs -->
    <section class="kpis" aria-label="Key metrics">
      <div v-for="kpi in kpis" :key="kpi.label" class="kpi card">
        <div class="kpi-label">
          <component :is="kpi.icon" :size="16" aria-hidden="true" />{{ kpi.label }}
        </div>
        <div v-if="loading" class="skeleton kpi-skel"></div>
        <div v-else class="kpi-value tabular">{{ kpi.value }}</div>
        <div v-if="kpi.hint && !loading" class="kpi-hint">{{ kpi.hint }}</div>
      </div>
    </section>

    <div class="overview-grid">
      <!-- Sign-in methods -->
      <section class="card" aria-labelledby="methods-title">
        <div class="card-header">
          <h2 id="methods-title">Sign-in methods</h2>
          <p>How accounts authenticate</p>
        </div>
        <div v-if="loading" class="skeleton" style="height: 10px;"></div>
        <template v-else-if="providers.length">
          <div class="breakdown-bar" role="img" :aria-label="breakdownSummary">
            <span v-for="p in providers" :key="p.name" :style="{ width: `${p.share}%`, background: p.color }"></span>
          </div>
          <ul class="legend">
            <li v-for="p in providers" :key="p.name">
              <span class="legend-swatch" :style="{ background: p.color }" aria-hidden="true"></span>
              <span class="spacer">{{ p.label }}</span>
              <span class="tabular text-muted">{{ p.count.toLocaleString() }}</span>
              <span class="tabular legend-share">{{ p.share }}%</span>
            </li>
          </ul>
        </template>
        <p v-else class="text-muted text-md">No accounts yet.</p>
      </section>

      <!-- Recent activity -->
      <section class="card card-flush" aria-labelledby="recent-title">
        <div class="card-header recent-header">
          <div>
            <h2 id="recent-title">Recently signed in</h2>
            <p>Latest account activity</p>
          </div>
          <router-link to="/admin/users" class="link text-md">View all</router-link>
        </div>
        <SkeletonRows v-if="loading" :rows="4" />
        <div v-else-if="recent.length" class="list">
          <router-link v-for="u in recent" :key="u.id" :to="`/admin/users/${u.id}`" class="list-row">
            <span class="avatar avatar-sm avatar-placeholder">{{ u.username[0].toUpperCase() }}</span>
            <div class="list-row-main">
              <div class="list-row-title"><span class="truncate">{{ u.username }}</span></div>
              <div class="list-row-sub truncate">{{ u.email }}</div>
            </div>
            <span class="text-sm text-muted tabular">{{ relativeTime(u.last_login_at) }}</span>
            <ChevronRight :size="18" class="list-row-chevron" aria-hidden="true" />
          </router-link>
        </div>
        <EmptyState v-else title="No sign-ins yet" text="Activity shows up here once users sign in." />
      </section>
    </div>
  </div>
</template>

<script>
import { Users, UserCheck, UserPlus, ShieldCheck, ChevronRight, Inbox } from 'lucide-vue-next';
import api from '@/api';
import ErrorAlert from '@/components/ui/ErrorAlert.vue';
import SkeletonRows from '@/components/ui/SkeletonRows.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import { relativeTime, formatNumber } from '@/utils/format';
import { providerName } from '@/utils/messages';
import { requestCounts } from '@/utils/adminRequests';

const PROVIDER_COLORS = ['var(--primary)', '#a78bfa', '#f59e0b', '#34d399', '#f472b6', '#94a3b8'];

export default {
  name: 'AdminDashboard',
  components: { ErrorAlert, Users, ChevronRight, Inbox, SkeletonRows, EmptyState },
  data() {
    return { analytics: {}, recent: [], loading: true, error: '', counts: requestCounts };
  },
  computed: {
    kpis() {
      const a = this.analytics;
      const activeShare = a.total_users ? Math.round((a.active_users / a.total_users) * 100) : null;
      return [
        { label: 'Total users', value: formatNumber(a.total_users), icon: Users },
        { label: 'Active', value: formatNumber(a.active_users), icon: UserCheck,
          hint: activeShare === null ? '' : `${activeShare}% of all accounts` },
        { label: 'New this week', value: formatNumber(a.new_this_week), icon: UserPlus },
        { label: 'Administrators', value: formatNumber(a.admin_count), icon: ShieldCheck },
      ];
    },
    providers() {
      const breakdown = this.analytics.provider_breakdown || {};
      const total = Object.values(breakdown).reduce((sum, n) => sum + n, 0);
      if (!total) return [];
      return Object.entries(breakdown)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count], i) => ({
          name,
          count,
          label: providerName(name),
          share: Math.round((count / total) * 100),
          color: PROVIDER_COLORS[i % PROVIDER_COLORS.length],
        }));
    },
    breakdownSummary() {
      return this.providers.map(p => `${p.label} ${p.share}%`).join(', ');
    },
  },
  created() {
    this.load();
  },
  methods: {
    relativeTime,
    async load() {
      this.loading = true;
      this.error = '';
      try {
        const [analytics, users] = await Promise.all([
          api.getAnalytics(),
          api.getAdminUsers({ perPage: 5, sort: 'last_login' }),
        ]);
        this.analytics = analytics;
        this.recent = users.users;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.requests-banner { margin-bottom: var(--space-md); align-items: center; text-decoration: none; }
.requests-banner:hover { filter: brightness(1.05); }

.kpis {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

@media (min-width: 768px) {
  .kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-md); }
}

.kpi { padding: var(--space-md); }
.kpi + .kpi { margin-top: 0; }

.kpi-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.kpi-value {
  font-size: var(--text-2xl);
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-top: var(--space-xs);
}

.kpi-skel { height: 28px; width: 60%; margin-top: 10px; }
.kpi-hint { font-size: var(--text-xs); color: var(--text-subtle); margin-top: 2px; }

.overview-grid {
  display: grid;
  gap: var(--space-md);
}

.overview-grid .card + .card { margin-top: 0; }

@media (min-width: 1024px) {
  .overview-grid { grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); align-items: start; }
}

.breakdown-bar {
  display: flex;
  height: 10px;
  border-radius: var(--radius-full);
  overflow: hidden;
  gap: 2px;
  background: var(--surface-2);
}

.breakdown-bar span { min-width: 4px; }

.legend { list-style: none; margin-top: var(--space-md); display: flex; flex-direction: column; }

.legend li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  font-size: var(--text-md);
  border-bottom: 1px solid var(--border);
}

.legend li:last-child { border-bottom: none; }
.legend-swatch { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
.legend-share { width: 3.5em; text-align: right; }

.recent-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-lg) var(--space-lg) var(--space-md);
  margin: 0;
  border-bottom: 1px solid var(--border);
}
</style>
