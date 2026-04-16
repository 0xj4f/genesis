<template>
  <div class="page-container">
    <div class="sessions-layout">
      <div class="card">
        <div class="card-header">
          <div class="sessions-header-row">
            <div>
              <h2>Active Sessions</h2>
              <p>Devices currently signed into your account</p>
            </div>
            <button v-if="sessions.length > 1" class="btn btn-danger btn-sm" @click="handleRevokeAll">
              Logout All Others
            </button>
          </div>
        </div>

        <div v-if="loading" class="text-center">
          <div class="spinner" style="width: 24px; height: 24px; margin: var(--space-lg) auto;"></div>
        </div>

        <div v-else-if="sessions.length === 0" class="text-center text-muted" style="padding: var(--space-xl);">
          No active sessions found.
        </div>

        <div v-else class="session-list">
          <div v-for="s in sessions" :key="s.id" class="session-row" :class="{ 'session-current': s.is_current }">
            <div class="session-info">
              <div class="session-device">
                <span class="device-icon">{{ deviceEmoji(s.device_name) }}</span>
                <div>
                  <strong>{{ s.device_name || 'Unknown device' }}</strong>
                  <span v-if="s.is_current" class="badge badge-accent" style="margin-left: 8px;">This device</span>
                </div>
              </div>
              <div class="session-meta text-sm text-muted">
                <span>{{ s.ip_address || 'Unknown IP' }}</span>
                <span>&middot;</span>
                <span>{{ s.login_method }}</span>
                <span>&middot;</span>
                <span>{{ formatDate(s.last_activity_at) }}</span>
              </div>
            </div>
            <button v-if="!s.is_current" class="btn btn-outline btn-sm" @click="handleRevoke(s.id)">
              Revoke
            </button>
          </div>
        </div>

        <div v-if="error" class="alert alert-error mt-md">{{ error }}</div>
        <div v-if="successMsg" class="alert alert-success mt-md">{{ successMsg }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/api';

export default {
  name: 'SessionsView',
  data() {
    return {
      sessions: [],
      loading: true,
      error: '',
      successMsg: '',
    };
  },
  async created() {
    await this.loadSessions();
  },
  methods: {
    async loadSessions() {
      this.loading = true;
      try {
        const data = await api.getSessions(this.$store.state.accessToken);
        this.sessions = data.sessions || [];
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    async handleRevoke(id) {
      this.error = '';
      try {
        await api.revokeSession(this.$store.state.accessToken, id);
        this.successMsg = 'Session revoked.';
        setTimeout(() => { this.successMsg = ''; }, 3000);
        await this.loadSessions();
      } catch (e) {
        this.error = e.message;
      }
    },
    async handleRevokeAll() {
      this.error = '';
      try {
        const data = await api.revokeAllSessions(this.$store.state.accessToken);
        this.successMsg = data.message || 'All other sessions revoked.';
        setTimeout(() => { this.successMsg = ''; }, 3000);
        await this.loadSessions();
      } catch (e) {
        this.error = e.message;
      }
    },
    deviceEmoji(name) {
      if (!name) return '?';
      const n = name.toLowerCase();
      if (n.includes('mobile') || n.includes('android') || n.includes('iphone')) return '(M)';
      if (n.includes('mac')) return '(D)';
      if (n.includes('windows')) return '(W)';
      if (n.includes('linux')) return '(L)';
      return '(?)';
    },
    formatDate(d) {
      if (!d) return '';
      const date = new Date(d);
      const now = new Date();
      const diffMs = now - date;
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return 'Just now';
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h ago`;
      return date.toLocaleDateString();
    },
  },
};
</script>

<style scoped>
.sessions-layout {
  max-width: 700px;
  margin: 0 auto;
}

.sessions-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.session-list {
  border-top: 1px solid var(--border-color);
}

.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--bg-muted);
}

.session-row:last-child { border-bottom: none; }

.session-current {
  background: var(--bg-muted);
  margin: 0 calc(-1 * var(--space-xl));
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-md);
}

.session-device {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.device-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
}

.session-meta {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-xs);
  margin-left: calc(36px + var(--space-sm));
}
</style>
