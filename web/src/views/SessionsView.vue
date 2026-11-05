<template>
  <div class="page-container narrow">
    <div class="page-header">
      <div>
        <h1>Devices &amp; sessions</h1>
        <p>Where your account is signed in right now.</p>
      </div>
      <button v-if="otherSessions.length" class="btn btn-danger-outline btn-sm" @click="handleRevokeAll">
        <LogOut :size="15" aria-hidden="true" />Sign out other devices
      </button>
    </div>

    <ErrorAlert v-if="error" :message="error" class="mb-md" @retry="loadSessions" />

    <div class="card card-flush">
      <SkeletonRows v-if="loading" :rows="3" />

      <EmptyState v-else-if="!sessions.length" title="No active sessions"
                  text="Sessions appear here when you sign in on a device.">
        <template #icon><MonitorSmartphone :size="22" /></template>
      </EmptyState>

      <ul v-else class="list" aria-label="Sessions">
        <li v-for="s in sortedSessions" :key="s.id" class="list-row session-row">
          <span class="device-icon" :class="{ current: s.is_current }" aria-hidden="true">
            <component :is="deviceIcon(s.device_name)" :size="20" />
          </span>
          <div class="list-row-main">
            <div class="list-row-title">
              <span class="wrap-anywhere">{{ s.device_name || 'Unknown device' }}</span>
              <span v-if="s.is_current" class="badge badge-success">This device</span>
            </div>
            <div class="list-row-sub">
              <span>{{ s.is_current ? 'Active now' : `Active ${relativeTime(s.last_activity_at).toLowerCase()}` }}</span>
              <span aria-hidden="true"> · </span>
              <span>{{ methodLabel(s.login_method) }}</span>
              <template v-if="s.ip_address">
                <span aria-hidden="true"> · </span><span class="mono">{{ s.ip_address }}</span>
              </template>
            </div>
          </div>
          <button v-if="!s.is_current" class="btn btn-ghost btn-sm" :aria-label="`Sign out ${s.device_name || 'this device'}`"
                  @click="handleRevoke(s)">
            Sign out
          </button>
        </li>
      </ul>
    </div>

    <p class="text-sm text-subtle mt-md">
      Don't recognise a device? Sign it out, then change your password from your profile.
    </p>
  </div>
</template>

<script>
import { LogOut, MonitorSmartphone, Smartphone, Tablet, Laptop, Monitor } from 'lucide-vue-next';
import api from '@/api';
import ErrorAlert from '@/components/ui/ErrorAlert.vue';
import SkeletonRows from '@/components/ui/SkeletonRows.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import { relativeTime } from '@/utils/format';
import { providerName } from '@/utils/messages';
import { toast, confirmAction } from '@/utils/feedback';

export default {
  name: 'SessionsView',
  components: { ErrorAlert, LogOut, MonitorSmartphone, SkeletonRows, EmptyState },
  data() {
    return {
      sessions: [],
      loading: true,
      error: '',
    };
  },
  computed: {
    otherSessions() { return this.sessions.filter(s => !s.is_current); },
    sortedSessions() {
      return [...this.sessions].sort((a, b) => Number(b.is_current) - Number(a.is_current)
        || new Date(b.last_activity_at || 0) - new Date(a.last_activity_at || 0));
    },
  },
  async created() {
    await this.loadSessions();
  },
  methods: {
    relativeTime,
    async loadSessions() {
      this.loading = true;
      this.error = '';
      try {
        const data = await api.getSessions();
        this.sessions = data.sessions || [];
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    async handleRevoke(session) {
      this.error = '';
      try {
        await api.revokeSession(session.id);
        toast(`Signed out ${session.device_name || 'device'}`);
        await this.loadSessions();
      } catch (e) {
        this.error = e.message;
      }
    },
    async handleRevokeAll() {
      const count = this.otherSessions.length;
      const ok = await confirmAction({
        title: `Sign out ${count} other ${count === 1 ? 'device' : 'devices'}?`,
        message: 'They will need to sign in again. This device stays signed in.',
        confirmLabel: 'Sign out devices',
        danger: true,
      });
      if (!ok) return;
      this.error = '';
      try {
        const data = await api.revokeAllSessions();
        toast(data.message || 'Other devices signed out');
        await this.loadSessions();
      } catch (e) {
        this.error = e.message;
      }
    },
    deviceIcon(name) {
      const n = (name || '').toLowerCase();
      if (n.includes('ipad') || n.includes('tablet')) return Tablet;
      if (n.includes('mobile') || n.includes('android') || n.includes('iphone')) return Smartphone;
      if (n.includes('mac') || n.includes('windows') || n.includes('linux') || n.includes('chrome os')) return Laptop;
      return Monitor;
    },
    methodLabel(method) {
      if (!method || method === 'password') return 'Password';
      return providerName(method);
    },
  },
};
</script>

<style scoped>
.narrow { max-width: 720px; }

.list { list-style: none; }
.session-row { align-items: center; }
.session-row .list-row-title { flex-wrap: wrap; row-gap: 4px; }
.list-row-sub { overflow-wrap: anywhere; }

.device-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-muted);
}

.device-icon.current { background: var(--success-soft); color: var(--success); border-color: transparent; }
</style>
