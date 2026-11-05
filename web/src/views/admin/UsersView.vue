<template>
  <div class="page-container admin-page">
    <div class="page-header">
      <div>
        <h1>Users</h1>
        <p>{{ loading && !users.length ? 'Loading accounts…' : `${total.toLocaleString()} ${total === 1 ? 'account' : 'accounts'}` }}</p>
      </div>
      <button class="btn btn-primary" @click="creating = true">
        <UserPlus :size="16" aria-hidden="true" />New user
      </button>
    </div>

    <div class="toolbar">
      <div class="input-wrap has-leading search">
        <span class="input-leading"><Search :size="16" aria-hidden="true" /></span>
        <label for="user-search" class="sr-only">Search users</label>
        <input id="user-search" v-model="search" type="search" class="form-input" placeholder="Search by username or email"
               autocapitalize="none" autocorrect="off" spellcheck="false" enterkeyhint="search" @input="onSearch" />
      </div>
      <div class="chips filters" role="group" aria-label="Filters">
        <label v-for="f in filterDefs" :key="f.key" class="chip chip-select" :aria-pressed="String(!!filters[f.key])">
          <select :value="filters[f.key]" :aria-label="f.label" @change="setFilter(f.key, $event.target.value)">
            <option value="">{{ f.any }}</option>
            <option v-for="o in f.options" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
          <ChevronDown :size="14" aria-hidden="true" />
        </label>
        <button v-if="hasFilters" class="chip" @click="clearFilters">
          <X :size="14" aria-hidden="true" />Clear
        </button>
      </div>
    </div>

    <ErrorAlert v-if="error" :message="error" class="mb-md" @retry="loadUsers" />

    <div class="card card-flush">
      <SkeletonRows v-if="loading && !users.length" :rows="6" />

      <EmptyState v-else-if="!users.length" title="No users found"
                  :text="hasFilters || search ? 'Try a different search or clear the filters.' : 'Accounts appear here once people register.'">
        <template #icon><Users :size="22" /></template>
        <button v-if="hasFilters || search" class="btn btn-secondary btn-sm" @click="clearFilters">Clear search and filters</button>
      </EmptyState>

      <template v-else>
        <!-- Phones and tablets: tappable rows -->
        <div class="list only-narrow" :class="{ dimmed: loading }">
          <router-link v-for="u in users" :key="u.id" :to="userLink(u.id)" class="list-row">
            <span class="avatar avatar-placeholder">{{ u.username[0].toUpperCase() }}</span>
            <div class="list-row-main">
              <div class="list-row-title">
                <span class="truncate">{{ u.username }}</span>
                <span v-if="u.role !== 'user'" class="badge cap" :class="roleBadge(u.role)">{{ u.role }}</span>
              </div>
              <div class="list-row-sub truncate">{{ u.email }}</div>
              <div class="row-meta">
                <StatusBadge :label="u.disabled ? 'Disabled' : 'Active'" :tone="u.disabled ? 'danger' : 'success'" />
                <span v-if="u.must_change_password" class="badge badge-warning">Must change password</span>
                <span class="text-sm text-subtle">{{ providerName(u.auth_provider) }} · {{ u.last_login_at ? relativeTime(u.last_login_at) : 'Never signed in' }}</span>
              </div>
            </div>
            <ChevronRight :size="18" class="list-row-chevron" aria-hidden="true" />
          </router-link>
        </div>

        <!-- Desktop: table -->
        <table class="table only-wide" :class="{ dimmed: loading }">
          <thead>
            <tr>
              <th scope="col">User</th>
              <th scope="col">Role</th>
              <th scope="col">Status</th>
              <th scope="col">Sign-in</th>
              <th scope="col">Last login</th>
              <th scope="col"><span class="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id" class="row-link">
              <td>
                <div class="row user-cell">
                  <span class="avatar avatar-sm avatar-placeholder">{{ u.username[0].toUpperCase() }}</span>
                  <div class="wrap-anywhere">
                    <router-link :to="userLink(u.id)" class="stretched">{{ u.username }}</router-link>
                    <div class="text-sm text-muted truncate">{{ u.email }}</div>
                  </div>
                </div>
              </td>
              <td><span class="badge cap" :class="roleBadge(u.role)">{{ u.role }}</span></td>
              <td>
                <div class="badge-row">
                  <StatusBadge :label="u.disabled ? 'Disabled' : 'Active'" :tone="u.disabled ? 'danger' : 'success'" />
                  <span v-if="u.must_change_password" class="badge badge-warning">Must change password</span>
                </div>
              </td>
              <td class="text-muted">{{ providerName(u.auth_provider) }}</td>
              <td class="text-muted tabular" :title="u.last_login_at ? dateTime(u.last_login_at) : ''">{{ relativeTime(u.last_login_at) }}</td>
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

    <UserDetailPane :open="!!selectedId" :user-id="selectedId" @close="closeDetail" @updated="loadUsers" />
    <NewUserSheet :open="creating" @close="creating = false" @created="onCreated" />
  </div>
</template>

<script>
import { Search, ChevronDown, ChevronRight, ChevronLeft, X, Users, UserPlus } from 'lucide-vue-next';
import api from '@/api';
import ErrorAlert from '@/components/ui/ErrorAlert.vue';
import UserDetailPane from '@/components/admin/UserDetailPane.vue';
import NewUserSheet from '@/components/admin/NewUserSheet.vue';
import SkeletonRows from '@/components/ui/SkeletonRows.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import { relativeTime, dateTime, roleBadge } from '@/utils/format';
import { providerName } from '@/utils/messages';

const PER_PAGE = 20;
// Each filter maps to a query parameter of GET /admin/users and of this page's URL.
const FILTERS = [
  { key: 'role', label: 'Role', any: 'Any role', options: [
    { value: 'user', label: 'User' }, { value: 'admin', label: 'Admin' }, { value: 'root', label: 'Root' }] },
  { key: 'status', label: 'Status', any: 'Any status', options: [
    { value: 'active', label: 'Active' }, { value: 'disabled', label: 'Disabled' }] },
  { key: 'provider', label: 'Sign-in method', any: 'Any sign-in', options: [
    { value: 'native', label: 'Password' }, { value: 'google', label: 'Google' },
    { value: 'github', label: 'GitHub' }, { value: 'facebook', label: 'Facebook' }] },
];
const FILTER_KEYS = FILTERS.map(f => f.key);

export default {
  name: 'AdminUsers',
  components: {
    ErrorAlert, Search, ChevronDown, ChevronRight, ChevronLeft, X, Users, UserPlus,
    UserDetailPane, NewUserSheet, SkeletonRows, EmptyState, StatusBadge,
  },
  data() {
    return {
      users: [],
      total: 0,
      totalPages: 1,
      loading: true,
      error: '',
      creating: false,
      search: this.$route.query.q || '',
      searchTimer: null,
    };
  },
  computed: {
    // List state lives in the URL so back, reload of a link and sharing restore it.
    selectedId() { return this.$route.params.id || null; },
    page() { return Number(this.$route.query.page) || 1; },
    filterDefs() { return FILTERS; },
    filters() {
      return Object.fromEntries(FILTER_KEYS.map(key => [key, this.$route.query[key] || '']));
    },
    hasFilters() { return FILTER_KEYS.some(key => this.filters[key]); },
    // Everything that changes the list (not the open user) refetches it.
    listQuery() { return JSON.stringify([this.$route.query.q, this.page, this.filters]); },
  },
  watch: {
    listQuery() { this.loadUsers(); },
  },
  created() {
    this.loadUsers();
  },
  beforeUnmount() { clearTimeout(this.searchTimer); },
  methods: {
    relativeTime,
    dateTime,
    roleBadge,
    async loadUsers() {
      this.loading = true;
      this.error = '';
      try {
        const data = await api.getAdminUsers({
          page: this.page, perPage: PER_PAGE, search: this.$route.query.q, ...this.filters,
        });
        this.users = data.users;
        this.total = data.total;
        this.totalPages = data.total_pages;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    updateQuery(changes) {
      const query = { ...this.$route.query, ...changes };
      for (const key of Object.keys(query)) {
        if (!query[key] || (key === 'page' && query[key] === 1)) delete query[key];
      }
      this.$router.replace({ name: 'AdminUsers', params: {}, query });
    },
    onSearch() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => this.updateQuery({ q: this.search.trim(), page: 1 }), 300);
    },
    setFilter(key, value) {
      this.updateQuery({ [key]: value, page: 1 });
    },
    clearFilters() {
      this.search = '';
      this.$router.replace({ name: 'AdminUsers', params: {}, query: {} });
    },
    goPage(page) {
      this.updateQuery({ page });
      window.scrollTo({ top: 0 });
    },
    userLink(id) {
      return { name: 'AdminUsers', params: { id }, query: this.$route.query };
    },
    closeDetail() {
      // Opened from inside the list: step back so history stays tidy; opened from a link: go to the list.
      if (window.history.state?.back?.startsWith('/admin/users')) this.$router.back();
      else this.$router.replace({ name: 'AdminUsers', params: {}, query: this.$route.query });
    },
    providerName,
    async onCreated(user) {
      this.creating = false;
      await this.loadUsers();
      this.$router.push({ name: 'AdminUsers', params: { id: user.id }, query: this.$route.query });
    },
  },
};
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

@media (min-width: 768px) {
  .toolbar { flex-direction: row; align-items: center; }
  .search { width: 340px; }
}

.filters { align-items: center; }

.chip-select { position: relative; padding: 0; }

.chip-select select {
  height: 100%;
  min-height: inherit;
  padding: 0 30px 0 12px;
  border-radius: inherit;
  -webkit-appearance: none;
  appearance: none;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
  outline: none;
}

.chip-select select:focus-visible { outline: none; }
.chip-select:has(select:focus-visible) { outline: 2px solid var(--ring); outline-offset: 2px; }
.chip-select svg { position: absolute; right: 10px; pointer-events: none; }
</style>
