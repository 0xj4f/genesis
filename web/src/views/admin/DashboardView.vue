<template>
  <div class="admin-container">
    <div class="admin-header">
      <h1>Admin<span class="warn">_Dashboard</span></h1>
      <p class="text-muted text-sm">system overview // user management</p>
    </div>

    <!-- Analytics -->
    <AnalyticsCards :analytics="analytics" />

    <!-- User Table -->
    <div class="card mt-lg table-card">
      <div class="table-header">
        <h2>Users</h2>
        <div class="search-box">
          <input v-model="search" class="form-input" placeholder="search users..."
                 @input="debounceSearch" />
        </div>
      </div>

      <div v-if="loadingUsers" class="text-center" style="padding: var(--space-xl);">
        <div class="spinner" style="width: 24px; height: 24px; margin: 0 auto;"></div>
      </div>

      <table v-else class="user-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
            <th>Provider</th>
            <th>Status</th>
            <th>Last Login</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" @click="openDetail(u.id)" class="user-row">
            <td class="col-username">{{ u.username }}</td>
            <td class="col-email">{{ u.email }}</td>
            <td><span class="badge" :class="roleBadge(u.role)">{{ u.role }}</span></td>
            <td><span class="text-muted">{{ u.auth_provider }}</span></td>
            <td>
              <span class="status-dot" :class="u.disabled ? 'dot-red' : 'dot-green'"></span>
              {{ u.disabled ? 'disabled' : 'active' }}
            </td>
            <td class="text-muted">{{ formatDate(u.last_login_at) }}</td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="6" class="text-center text-muted" style="padding: var(--space-xl);">No users found</td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination">
        <button class="btn btn-ghost btn-sm" :disabled="page <= 1" @click="goPage(page - 1)">&lt; Prev</button>
        <span class="page-info">{{ page }} / {{ totalPages }} <span class="text-muted">({{ total }} users)</span></span>
        <button class="btn btn-ghost btn-sm" :disabled="page >= totalPages" @click="goPage(page + 1)">Next &gt;</button>
      </div>
    </div>

    <!-- Detail Pane -->
    <UserDetailPane
      :visible="!!selectedUserId"
      :userId="selectedUserId"
      @close="selectedUserId = null"
      @updated="refresh"
    />
  </div>
</template>

<script>
import api from '@/api';
import AnalyticsCards from '@/components/admin/AnalyticsCards.vue';
import UserDetailPane from '@/components/admin/UserDetailPane.vue';

export default {
  name: 'AdminDashboard',
  components: { AnalyticsCards, UserDetailPane },
  data() {
    return {
      analytics: {},
      users: [],
      total: 0,
      page: 1,
      totalPages: 1,
      search: '',
      loadingUsers: false,
      selectedUserId: null,
      searchTimer: null,
    };
  },
  computed: {
    token() { return this.$store.state.adminToken; },
  },
  async created() {
    await Promise.all([this.loadAnalytics(), this.loadUsers()]);
  },
  methods: {
    async loadAnalytics() {
      try {
        this.analytics = await api.getAnalytics(this.token);
      } catch { /* ignore */ }
    },
    async loadUsers() {
      this.loadingUsers = true;
      try {
        const data = await api.getAdminUsers(this.token, this.page, 20, this.search);
        this.users = data.users;
        this.total = data.total;
        this.totalPages = data.total_pages;
      } catch { /* ignore */ }
      finally { this.loadingUsers = false; }
    },
    debounceSearch() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => {
        this.page = 1;
        this.loadUsers();
      }, 300);
    },
    goPage(p) {
      this.page = p;
      this.loadUsers();
    },
    openDetail(id) {
      this.selectedUserId = id;
    },
    async refresh() {
      await Promise.all([this.loadAnalytics(), this.loadUsers()]);
    },
    roleBadge(role) {
      if (role === 'root') return 'badge-danger';
      if (role === 'admin') return 'badge-accent';
      return '';
    },
    formatDate(d) {
      if (!d) return 'Never';
      const date = new Date(d);
      const now = new Date();
      const diff = Math.floor((now - date) / 60000);
      if (diff < 1) return 'Just now';
      if (diff < 60) return `${diff}m ago`;
      if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
      return date.toLocaleDateString();
    },
  },
};
</script>

<style scoped>
.admin-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl);
}

.admin-header {
  margin-bottom: var(--space-xl);
}

.admin-header h1 {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 600;
}

.warn { color: #f59e0b; }

.table-card { padding: 0; overflow: hidden; }

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--border-color);
}

.table-header h2 {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
}

.search-box { width: 280px; }
.search-box .form-input { font-size: var(--text-xs); padding: 8px 12px; }

.user-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.user-table th {
  text-align: left;
  padding: 10px var(--space-md);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 500;
  font-size: 0.65rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-muted);
}

.user-table td {
  padding: 12px var(--space-md);
  border-bottom: 1px solid var(--border-color);
}

.user-row {
  cursor: pointer;
  transition: background var(--transition-fast);
}

.user-row:hover {
  background: var(--bg-hover);
}

.col-username { color: var(--accent); font-weight: 500; }
.col-email { color: var(--text-secondary); }

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 6px;
}

.dot-green { background: var(--color-success); box-shadow: 0 0 6px rgba(34, 197, 94, 0.4); }
.dot-red { background: var(--color-error); box-shadow: 0 0 6px rgba(239, 68, 68, 0.4); }

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  padding: var(--space-md);
  border-top: 1px solid var(--border-color);
}

.page-info {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
</style>
