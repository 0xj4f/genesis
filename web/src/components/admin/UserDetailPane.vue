<template>
  <transition name="slide">
    <div v-if="visible" class="pane-overlay" @click.self="$emit('close')">
      <div class="pane">
        <div class="pane-header">
          <h2>User Detail</h2>
          <button class="btn btn-ghost btn-sm" @click="$emit('close')">ESC</button>
        </div>

        <div v-if="loading" class="text-center" style="padding: var(--space-2xl);">
          <div class="spinner" style="width: 28px; height: 28px; margin: 0 auto;"></div>
        </div>

        <div v-else-if="user" class="pane-body">
          <!-- Avatar + Name -->
          <div class="pane-profile">
            <img v-if="avatar" :src="avatar" class="avatar avatar-lg" alt="Avatar" referrerpolicy="no-referrer" />
            <div v-else class="avatar avatar-lg avatar-placeholder">
              {{ (user.username || '?')[0].toUpperCase() }}
            </div>
            <div>
              <h3 v-if="user.profile">{{ user.profile.given_name }} {{ user.profile.family_name }}</h3>
              <h3 v-else>{{ user.username }}</h3>
              <p class="text-muted text-sm">{{ user.email }}</p>
              <div class="badge-row mt-sm">
                <span class="badge" :class="roleBadge(user.role)">{{ user.role }}</span>
                <span class="badge badge-success" v-if="!user.disabled">active</span>
                <span class="badge badge-danger" v-else>disabled</span>
              </div>
            </div>
          </div>

          <!-- Details -->
          <div class="pane-details">
            <div class="detail-row" v-for="item in details" :key="item.label">
              <span class="detail-label">{{ item.label }}</span>
              <span class="detail-value">{{ item.value }}</span>
            </div>
          </div>

          <!-- Actions (hidden when the API would refuse them; the API still decides) -->
          <div v-if="canManage" class="pane-actions">
            <template v-if="isRootAdmin && !isSelf">
              <div class="form-group">
                <label for="role">Role</label>
                <select v-model="selectedRole" id="role" class="form-input">
                  <option v-for="role in roles" :key="role" :value="role">{{ role }}</option>
                </select>
              </div>
              <button class="btn btn-primary btn-sm" @click="changeRole" :disabled="selectedRole === user.role">
                Update Role
              </button>
            </template>

            <form v-if="!isSelf" @submit.prevent="resetPassword" class="stack mt-md">
              <label for="reset-password">Set a new password (signs the user out everywhere)</label>
              <input v-model="newPassword" id="reset-password" type="password" class="form-input"
                     autocomplete="new-password" minlength="12" maxlength="128" required />
              <button type="submit" class="btn btn-outline btn-sm">Reset Password</button>
            </form>

            <div class="action-row mt-md" v-if="user.role !== 'root'">
              <button class="btn btn-outline btn-sm" @click="toggleStatus">
                {{ user.disabled ? 'Enable User' : 'Disable User' }}
              </button>
              <button class="btn btn-danger btn-sm" @click="deleteUser">
                Delete
              </button>
            </div>
          </div>
          <p v-else class="text-muted text-sm mt-md">Only ROOT can manage this account.</p>

          <div v-if="actionMsg" class="alert alert-success mt-md">{{ actionMsg }}</div>
          <div v-if="actionError" class="alert alert-error mt-md">{{ actionError }}</div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import { mapGetters, mapState } from 'vuex';
import api from '@/api';
import { assetUrl } from '@/utils/url';
import { passwordError } from '@/utils/validation';

export default {
  name: 'UserDetailPane',
  props: {
    visible: Boolean,
    userId: String,
  },
  emits: ['close', 'updated'],
  data() {
    return {
      user: null,
      loading: false,
      selectedRole: 'user',
      newPassword: '',
      actionMsg: '',
      actionError: '',
      roles: ['user', 'admin', 'root'],
    };
  },
  computed: {
    ...mapGetters(['isRootAdmin']),
    ...mapState(['adminUser']),
    avatar() { return assetUrl(this.user?.profile?.picture); },
    isSelf() { return !!this.adminUser && this.adminUser.id === this.user?.id; },
    // Mirrors the API policy: admins manage regular users; root manages everyone but other roots.
    canManage() {
      if (!this.user) return false;
      if (this.isSelf) return true;
      if (this.isRootAdmin) return this.user.role !== 'root';
      return this.user.role === 'user';
    },
    details() {
      if (!this.user) return [];
      const u = this.user;
      const items = [
        { label: 'ID', value: u.id },
        { label: 'Username', value: u.username },
        { label: 'Provider', value: u.auth_provider },
        { label: 'Native', value: u.is_native ? 'Yes' : 'No' },
        { label: 'Email verified', value: u.email_verified ? 'Yes' : 'No' },
        { label: 'Sessions', value: u.sessions_count },
        { label: 'Linked SSO', value: u.linked_providers?.length || 0 },
        { label: 'Last login', value: u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never' },
        { label: 'Login method', value: u.last_login_method || '-' },
        { label: 'Login IP', value: u.last_login_ip || '-' },
        { label: 'Created', value: u.created_at ? new Date(u.created_at).toLocaleString() : '-' },
      ];
      if (u.profile) {
        items.push({ label: 'Nickname', value: u.profile.nick_name || '-' });
        items.push({ label: 'Locale', value: u.profile.locale || '-' });
        items.push({ label: 'Timezone', value: u.profile.timezone || '-' });
      }
      return items;
    },
  },
  watch: {
    userId: {
      handler(id) { if (id) this.loadUser(id); },
      immediate: true,
    },
  },
  methods: {
    async loadUser(id) {
      this.loading = true;
      this.actionMsg = '';
      this.actionError = '';
      try {
        this.user = await api.getAdminUserDetail(id);
        this.selectedRole = this.user.role;
      } catch (e) { this.actionError = e.message; }
      finally { this.loading = false; }
    },
    async changeRole() {
      this.actionError = '';
      if (!confirm(`Change ${this.user.username}'s role to ${this.selectedRole}? They will be signed out.`)) return;
      try {
        await api.updateUserRole(this.userId, this.selectedRole);
        this.actionMsg = `Role updated to ${this.selectedRole}`;
        this.$emit('updated');
        await this.loadUser(this.userId);
        setTimeout(() => { this.actionMsg = ''; }, 2000);
      } catch (e) { this.actionError = e.message; }
    },
    async toggleStatus() {
      this.actionError = '';
      const verb = this.user.disabled ? 'Enable' : 'Disable';
      if (!confirm(`${verb} ${this.user.username}?`)) return;
      try {
        const res = await api.toggleUserStatus(this.userId);
        this.actionMsg = res.message;
        this.$emit('updated');
        await this.loadUser(this.userId);
        setTimeout(() => { this.actionMsg = ''; }, 2000);
      } catch (e) { this.actionError = e.message; }
    },
    async deleteUser() {
      if (!confirm('Permanently delete this user?')) return;
      try {
        await api.adminDeleteUser(this.userId);
        this.$emit('updated');
        this.$emit('close');
      } catch (e) { this.actionError = e.message; }
    },
    roleBadge(role) {
      if (role === 'root') return 'badge-danger';
      if (role === 'admin') return 'badge-accent';
      return '';
    },
    async resetPassword() {
      this.actionError = passwordError(this.newPassword);
      if (this.actionError) return;
      if (!confirm(`Set a new password for ${this.user.username}?`)) return;
      try {
        this.actionMsg = (await api.adminResetPassword(this.userId, this.newPassword)).message;
        this.newPassword = '';
        await this.loadUser(this.userId);
      } catch (e) { this.actionError = e.message; }
    },
  },
};
</script>

<style scoped>
.pane-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 200;
  display: flex;
  justify-content: flex-end;
}

.pane {
  width: 480px;
  max-width: 90vw;
  height: 100vh;
  background: var(--bg-card);
  border-left: 1px solid var(--border-color);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.pane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--border-color);
}

.pane-header h2 {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
}

.pane-body {
  padding: var(--space-lg);
  flex: 1;
}

.pane-profile {
  display: flex;
  gap: var(--space-lg);
  align-items: center;
  margin-bottom: var(--space-xl);
}

.pane-profile h3 {
  font-size: var(--text-xl);
  font-weight: 600;
}

.badge-row { display: flex; gap: var(--space-sm); flex-wrap: wrap; }

.pane-details {
  border-top: 1px solid var(--border-color);
  padding-top: var(--space-md);
  margin-bottom: var(--space-xl);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--bg-muted);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

.detail-label { color: var(--text-muted); }
.detail-value { color: var(--text-primary); text-align: right; max-width: 60%; word-break: break-all; }

.pane-actions {
  border-top: 1px solid var(--border-color);
  padding-top: var(--space-lg);
}

.action-row { display: flex; gap: var(--space-sm); }

/* Slide animation */
.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from .pane, .slide-leave-to .pane { transform: translateX(100%); }
.slide-enter-from, .slide-leave-to { opacity: 0; }
</style>
