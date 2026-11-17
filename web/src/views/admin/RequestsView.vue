<template>
  <div class="page-container admin-page">
    <div class="page-header">
      <div>
        <h1>Requests</h1>
        <p>Help users ask for. Until email is set up, you send temporary passwords yourself.</p>
      </div>
    </div>

    <div class="toolbar">
      <div class="segmented" role="radiogroup" aria-label="Status">
        <button v-for="s in statuses" :key="s.value" type="button" role="radio"
                :aria-checked="String(status === s.value)" @click="setStatus(s.value)">
          {{ s.label }}<span v-if="s.value === 'open' && counts.open" class="count tabular">{{ counts.open }}</span>
        </button>
      </div>
      <span class="chip" aria-pressed="true"><KeyRound :size="14" aria-hidden="true" />Password reset</span>
    </div>

    <ErrorAlert v-if="error" :message="error" class="mb-md" @retry="load" />

    <div class="card card-flush">
      <SkeletonRows v-if="loading && !requests.length" :rows="4" />

      <EmptyState v-else-if="!requests.length" :title="emptyTitle" :text="emptyText">
        <template #icon><Inbox :size="22" /></template>
      </EmptyState>

      <template v-else>
        <!-- Phones and tablets -->
        <div class="list only-narrow" :class="{ dimmed: loading }">
          <router-link v-for="r in requests" :key="r.id" :to="requestLink(r.id)" class="list-row">
            <span class="avatar avatar-placeholder">{{ r.user.username[0].toUpperCase() }}</span>
            <div class="list-row-main">
              <div class="list-row-title">
                <span class="truncate">{{ r.user.username }}</span>
                <span v-if="r.user.role !== 'user'" class="badge cap" :class="roleBadge(r.user.role)">{{ r.user.role }}</span>
              </div>
              <div class="list-row-sub truncate">{{ r.user.email }}</div>
              <div class="row-meta">
                <span class="badge"><KeyRound :size="12" aria-hidden="true" />{{ categoryLabel(r.category) }}</span>
                <span class="text-sm text-subtle">{{ whenLabel(r) }}</span>
              </div>
            </div>
            <ChevronRight :size="18" class="list-row-chevron" aria-hidden="true" />
          </router-link>
        </div>

        <!-- Desktop -->
        <table class="table only-wide" :class="{ dimmed: loading }">
          <thead>
            <tr>
              <th scope="col">User</th>
              <th scope="col">Request</th>
              <th scope="col">{{ status === 'open' ? 'Requested' : 'Closed' }}</th>
              <th scope="col">{{ status === 'open' ? 'Times' : 'By' }}</th>
              <th scope="col"><span class="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in requests" :key="r.id" class="row-link">
              <td>
                <div class="row user-cell">
                  <span class="avatar avatar-sm avatar-placeholder">{{ r.user.username[0].toUpperCase() }}</span>
                  <div class="wrap-anywhere">
                    <router-link :to="requestLink(r.id)" class="stretched">{{ r.user.username }}</router-link>
                    <div class="text-sm text-muted truncate">{{ r.user.email }}</div>
                  </div>
                </div>
              </td>
              <td><span class="badge"><KeyRound :size="12" aria-hidden="true" />{{ categoryLabel(r.category) }}</span></td>
              <td class="text-muted tabular" :title="dateTime(status === 'open' ? r.last_requested_at : r.resolved_at)">
                {{ relativeTime(status === 'open' ? r.last_requested_at : r.resolved_at) }}
              </td>
              <td class="text-muted tabular">{{ status === 'open' ? r.request_count : (r.resolved_by_username || '—') }}</td>
              <td class="chevron-cell"><ChevronRight :size="16" class="list-row-chevron" aria-hidden="true" /></td>
            </tr>
          </tbody>
        </table>
      </template>

      <nav v-if="totalPages > 1" class="pagination" aria-label="Pagination">
        <button class="btn btn-secondary btn-sm" :disabled="page <= 1 || loading" @click="goPage(page - 1)">
          <ChevronLeft :size="16" aria-hidden="true" />Previous
        </button>
        <span class="text-sm text-muted tabular">Page {{ page }} of {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">
          Next<ChevronRight :size="16" aria-hidden="true" />
        </button>
      </nav>
    </div>

    <!-- Request detail -->
    <AppSheet :open="!!selected" :title="selected ? `${categoryLabel(selected.category)} · ${selected.user.username}` : 'Request'"
              @close="closeDetail">
      <div v-if="selected" class="detail">
        <div class="sheet-identity">
          <span class="avatar avatar-lg avatar-placeholder">{{ selected.user.username[0].toUpperCase() }}</span>
          <div class="wrap-anywhere">
            <h3>{{ selected.user.username }}</h3>
            <p class="text-muted text-md">{{ selected.user.email }}</p>
            <div class="badge-row mt-sm">
              <span class="badge cap" :class="roleBadge(selected.user.role)">{{ selected.user.role }}</span>
              <StatusBadge :label="selected.user.disabled ? 'Disabled' : 'Active'" :tone="selected.user.disabled ? 'danger' : 'success'" />
              <span class="badge">{{ providerName(selected.user.auth_provider) }}</span>
            </div>
          </div>
        </div>

        <div v-if="selected.user.disabled" class="alert alert-warning">
          <TriangleAlert :size="18" aria-hidden="true" />
          <span>This account is disabled. A new password won't let them sign in until you enable it.</span>
        </div>
        <div v-else-if="selected.user.auth_provider !== 'native'" class="alert">
          <Info :size="18" aria-hidden="true" />
          <span>This account signs in with {{ providerName(selected.user.auth_provider) }}. A password adds a second way in.</span>
        </div>

        <section class="sheet-section">
          <h4 class="section-label">Request</h4>
          <dl class="dl card-lite">
            <div class="dl-row"><dt>Type</dt><dd>{{ categoryLabel(selected.category) }}</dd></div>
            <div class="dl-row"><dt>First asked</dt><dd>{{ dateTime(selected.created_at) }}</dd></div>
            <div class="dl-row" v-if="selected.request_count > 1">
              <dt>Asked again</dt><dd>{{ selected.request_count - 1 }}× · last {{ relativeTime(selected.last_requested_at) }}</dd>
            </div>
            <div class="dl-row" v-if="selected.requester_ip"><dt>From IP</dt><dd class="mono">{{ selected.requester_ip }}</dd></div>
            <div class="dl-row" v-if="selected.user_agent"><dt>Browser</dt><dd class="text-sm">{{ selected.user_agent }}</dd></div>
            <div class="dl-row" v-if="selected.status !== 'open'">
              <dt>{{ selected.status === 'resolved' ? 'Resolved' : 'Dismissed' }}</dt>
              <dd>{{ dateTime(selected.resolved_at) }}{{ selected.resolved_by_username ? ` by ${selected.resolved_by_username}` : '' }}</dd>
            </div>
          </dl>
        </section>

        <p v-if="selected.status === 'open'" class="form-hint mt-md">
          Confirm the request really came from {{ selected.user.username }} before sending a password, for example by
          contacting them through a channel you already know.
        </p>

        <div v-if="actionError" class="alert alert-error mt-md" role="alert">
          <CircleAlert :size="18" aria-hidden="true" />{{ actionError }}
        </div>

        <router-link :to="`/admin/users/${selected.user.id}`" class="btn btn-ghost btn-sm mt-md">
          <UserRound :size="15" aria-hidden="true" />View user
        </router-link>
      </div>

      <template v-if="selected && selected.status === 'open'" #footer>
        <button class="btn btn-secondary" :disabled="busy" @click="dismiss">Dismiss</button>
        <button class="btn btn-primary spacer" :disabled="busy" @click="generate">
          <span v-if="busy" class="spinner" aria-hidden="true"></span>
          <KeyRound v-else :size="16" aria-hidden="true" />Generate one-time password
        </button>
      </template>
    </AppSheet>

    <OneTimePasswordDialog :issued="issued" @close="onIssuedClosed" />
  </div>
</template>

<script>
import {
  Inbox, KeyRound, ChevronRight, ChevronLeft, CircleAlert, TriangleAlert, Info, UserRound,
} from 'lucide-vue-next';
import api from '@/api';
import ErrorAlert from '@/components/ui/ErrorAlert.vue';
import AppSheet from '@/components/ui/AppSheet.vue';
import SkeletonRows from '@/components/ui/SkeletonRows.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import OneTimePasswordDialog from '@/components/admin/OneTimePasswordDialog.vue';
import { relativeTime, dateTime, roleBadge } from '@/utils/format';
import { providerName } from '@/utils/messages';
import { toast, confirmAction } from '@/utils/feedback';
import { requestCounts, REQUEST_CATEGORIES } from '@/utils/adminRequests';

const PER_PAGE = 20;

export default {
  name: 'AdminRequests',
  components: {
    ErrorAlert, Inbox, KeyRound, ChevronRight, ChevronLeft, CircleAlert, TriangleAlert, Info, UserRound,
    AppSheet, SkeletonRows, EmptyState, StatusBadge, OneTimePasswordDialog,
  },
  data() {
    return {
      requests: [],
      totalPages: 1,
      loading: true,
      error: '',
      busy: false,
      actionError: '',
      counts: requestCounts,
      issued: null,
      // A request opened by link that is not on the current page of the list.
      linked: null,
      statuses: [
        { value: 'open', label: 'Open' },
        { value: 'resolved', label: 'Resolved' },
        { value: 'dismissed', label: 'Dismissed' },
      ],
    };
  },
  computed: {
    status() { return this.$route.query.status || 'open'; },
    page() { return Number(this.$route.query.page) || 1; },
    selectedId() { return this.$route.params.id || null; },
    selected() {
      if (!this.selectedId) return null;
      return this.requests.find(r => r.id === this.selectedId)
        || (this.linked?.id === this.selectedId ? this.linked : null);
    },
    emptyTitle() {
      return { open: 'No open requests', resolved: 'Nothing resolved yet', dismissed: 'Nothing dismissed' }[this.status];
    },
    emptyText() {
      return this.status === 'open' ? 'When someone uses "Forgot password?", their request appears here.' : '';
    },
    listQuery() { return `${this.status}|${this.page}`; },
  },
  watch: {
    listQuery() { this.load(); },
    selectedId() {
      this.actionError = '';
      if (!this.loading) this.loadLinked();
    },
  },
  created() {
    this.load();
  },
  methods: {
    relativeTime,
    dateTime,
    roleBadge,
    providerName,
    categoryLabel(category) { return REQUEST_CATEGORIES[category] || category; },
    whenLabel(r) {
      if (r.status !== 'open') {
        return `${r.status === 'resolved' ? 'Resolved' : 'Dismissed'} ${relativeTime(r.resolved_at).toLowerCase()}`;
      }
      const times = r.request_count > 1 ? ` · ${r.request_count} times` : '';
      return `Requested ${relativeTime(r.last_requested_at).toLowerCase()}${times}`;
    },
    async load() {
      this.loading = true;
      this.error = '';
      try {
        const data = await api.getRequests({ status: this.status, page: this.page, perPage: PER_PAGE });
        this.requests = data.requests;
        this.totalPages = data.total_pages;
        // The open list's total is the badge count; no second request needed.
        if (this.status === 'open') this.counts.open = data.total;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
      await this.loadLinked();
    },
    // Fetch a linked request that is not on this page; if it is gone, back to the list.
    async loadLinked() {
      if (!this.selectedId || this.selected) return;
      try {
        this.linked = await api.getRequest(this.selectedId);
      } catch {
        this.$router.replace({ name: 'AdminRequests', params: {}, query: this.$route.query });
      }
    },
    setStatus(status) {
      this.$router.replace({ name: 'AdminRequests', params: {}, query: status === 'open' ? {} : { status } });
    },
    goPage(page) {
      const query = { ...this.$route.query, page };
      if (page === 1) delete query.page;
      this.$router.replace({ name: 'AdminRequests', params: {}, query });
      window.scrollTo({ top: 0 });
    },
    requestLink(id) {
      return { name: 'AdminRequests', params: { id }, query: this.$route.query };
    },
    closeDetail() {
      if (window.history.state?.back?.startsWith('/admin/requests')) this.$router.back();
      else this.$router.replace({ name: 'AdminRequests', params: {}, query: this.$route.query });
    },
    async generate() {
      const request = this.selected;
      const ok = await confirmAction({
        title: `Generate a temporary password for ${request.user.username}?`,
        message: 'Any current password stops working and they are signed out everywhere. They must choose a new password when they sign in.',
        confirmLabel: 'Generate password',
      });
      if (!ok) return;
      this.busy = true;
      this.actionError = '';
      try {
        this.issued = await api.issueRequestPassword(request.id);
      } catch (e) {
        this.actionError = e.message;
      } finally {
        this.busy = false;
      }
    },
    async dismiss() {
      const request = this.selected;
      const ok = await confirmAction({
        title: `Dismiss ${request.user.username}'s request?`,
        message: 'Nothing changes on the account. Use this for requests that were mistakes or not genuine.',
        confirmLabel: 'Dismiss request',
      });
      if (!ok) return;
      this.busy = true;
      try {
        await api.dismissRequest(request.id);
        toast('Request dismissed');
        this.closeDetail();
        await this.load();
      } catch (e) {
        this.actionError = e.message;
      } finally {
        this.busy = false;
      }
    },
    async onIssuedClosed() {
      const username = this.issued.username;
      this.issued = null;
      toast(`Request resolved for ${username}`);
      this.closeDetail();
      await this.load();
    },
  },
};
</script>

<style scoped>
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-md); }

.count {
  margin-left: 6px;
  min-width: 18px;
  padding: 0 5px;
  border-radius: var(--radius-full);
  background: var(--primary);
  color: var(--on-primary);
  font-size: var(--text-xs);
  font-weight: 600;
  line-height: 18px;
  display: inline-block;
}
</style>
