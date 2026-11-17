<template>
  <AppSheet :open="open" :title="user ? user.username : 'User'" @close="$emit('close')">
    <div v-if="loading && !user" class="stack" aria-busy="true">
      <div class="row" style="gap: 16px;">
        <span class="skeleton" style="width: 64px; height: 64px; border-radius: 50%;"></span>
        <div class="stack-sm spacer">
          <span class="skeleton" style="height: 16px; width: 50%;"></span>
          <span class="skeleton" style="height: 12px; width: 70%;"></span>
        </div>
      </div>
      <span class="skeleton" style="height: 180px;"></span>
    </div>

    <ErrorAlert v-else-if="loadError" :message="loadError" @retry="loadUser(userId)" />

    <div v-else-if="user" class="detail">
      <!-- Identity -->
      <div class="sheet-identity">
        <img v-if="avatar" :src="avatar" class="avatar avatar-lg" alt="" referrerpolicy="no-referrer" />
        <span v-else class="avatar avatar-lg avatar-placeholder">{{ user.username[0].toUpperCase() }}</span>
        <div class="wrap-anywhere">
          <h3>{{ fullName || user.username }}</h3>
          <p class="text-muted text-md">{{ user.email }}</p>
          <div class="badge-row mt-sm">
            <span class="badge cap" :class="roleBadge(user.role)">{{ user.role }}</span>
            <StatusBadge :label="user.disabled ? 'Disabled' : 'Active'" :tone="user.disabled ? 'danger' : 'success'" />
            <span class="badge" :class="user.email_verified ? 'badge-success' : 'badge-warning'">
              {{ user.email_verified ? 'Email verified' : 'Email unverified' }}
            </span>
            <span v-if="isSelf" class="badge badge-primary">You</span>
            <span v-if="user.must_change_password" class="badge badge-warning" :title="dateTime(user.password_expires_at)">
              Must change password{{ user.password_expires_at ? ` · ${expiresIn(user.password_expires_at)}` : '' }}
            </span>
          </div>
        </div>
      </div>

      <router-link v-if="user.pending_request_id" :to="`/admin/requests/${user.pending_request_id}`" class="alert alert-warning pending">
        <Inbox :size="18" aria-hidden="true" />
        <span class="spacer">Asked for a password reset {{ relativeTime(user.pending_password_reset_at).toLowerCase() }}</span>
        <ChevronRight :size="16" aria-hidden="true" />
      </router-link>

      <!-- Account -->
      <section class="sheet-section">
        <h4 class="section-label">Account</h4>
        <dl class="dl card-lite">
          <div class="dl-row">
            <dt>User ID</dt>
            <dd><span class="mono">{{ shortId }}</span><CopyButton :value="user.id" what="user ID" /></dd>
          </div>
          <div class="dl-row"><dt>Username</dt><dd>{{ user.username }}</dd></div>
          <div class="dl-row"><dt>Sign-in method</dt><dd>{{ user.is_native ? 'Password' : providerName(user.auth_provider) }}</dd></div>
          <div class="dl-row"><dt>Created</dt><dd>{{ dateTime(user.created_at) }}</dd></div>
        </dl>
      </section>

      <!-- Security -->
      <section class="sheet-section">
        <h4 class="section-label">Security</h4>
        <dl class="dl card-lite">
          <div class="dl-row"><dt>Last sign-in</dt><dd>{{ user.last_login_at ? dateTime(user.last_login_at) : 'Never' }}</dd></div>
          <div class="dl-row" v-if="user.last_login_method"><dt>Method</dt><dd class="cap">{{ user.last_login_method }}</dd></div>
          <div class="dl-row" v-if="user.last_login_ip"><dt>IP address</dt><dd class="mono">{{ user.last_login_ip }}</dd></div>
          <div class="dl-row"><dt>Active sessions</dt><dd class="tabular">{{ user.sessions_count }}</dd></div>
          <div class="dl-row">
            <dt>Linked accounts</dt>
            <dd>
              <span v-if="!user.linked_providers?.length" class="text-muted">None</span>
              <span v-else class="badge-row">
                <span v-for="p in user.linked_providers" :key="p.provider" class="badge" :title="p.provider_email || ''">
                  {{ providerName(p.provider) }}
                </span>
              </span>
            </dd>
          </div>
        </dl>
      </section>

      <!-- Profile -->
      <section v-if="profileRows.length" class="sheet-section">
        <h4 class="section-label">Profile</h4>
        <dl class="dl card-lite">
          <div v-for="row in profileRows" :key="row.label" class="dl-row"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></div>
        </dl>
      </section>

      <!-- Management (hidden when the API would refuse it; the API still decides) -->
      <template v-if="canManage">
        <section v-if="isRootAdmin && !isSelf" class="sheet-section">
          <h4 class="section-label">Role</h4>
          <div class="card-lite pad">
            <div class="segmented role-picker" role="radiogroup" aria-label="Role">
              <button v-for="role in roles" :key="role" type="button" role="radio"
                      :aria-checked="String(selectedRole === role)" @click="selectedRole = role">{{ role }}</button>
            </div>
            <p class="form-hint mt-sm">Changing the role signs the user out of every session.</p>
            <button class="btn btn-primary btn-sm mt-md" :disabled="selectedRole === user.role || busy" @click="changeRole">
              Update role
            </button>
          </div>
        </section>

        <section v-if="!isSelf" class="sheet-section">
          <h4 class="section-label">Password</h4>
          <div class="card-lite pad stack-sm">
            <p class="form-hint">
              A one-time password lets {{ user.username }} sign in once and choose their own. You send it to them yourself.
            </p>
            <div class="row-wrap">
              <button class="btn btn-primary btn-sm" :disabled="busy" @click="generatePassword">
                <KeyRound :size="16" aria-hidden="true" />Generate one-time password
              </button>
              <button v-if="!showReset" class="btn btn-ghost btn-sm" @click="showReset = true">Set password manually</button>
            </div>
            <form v-if="showReset" class="stack-sm manual" novalidate @submit.prevent="resetPassword">
              <label for="reset-password" class="form-label">New password</label>
              <PasswordInput id="reset-password" v-model="newPassword" autocomplete="new-password"
                             :invalid="!!passwordProblem" describedby="reset-hint" />
              <p id="reset-hint" class="form-hint" :class="{ 'form-error': passwordProblem }">
                {{ passwordProblem || 'At least 12 characters with upper and lower case, a number and a symbol. Signs the user out everywhere.' }}
              </p>
              <label class="check">
                <input v-model="requireChange" type="checkbox" />
                <span>Require a new password at next sign-in</span>
              </label>
              <div class="row mt-xs">
                <button type="submit" class="btn btn-secondary btn-sm" :disabled="busy">Set password</button>
                <button type="button" class="btn btn-ghost btn-sm" @click="cancelReset">Cancel</button>
              </div>
            </form>
          </div>
        </section>

        <section v-if="user.role !== 'root' && !isSelf" class="sheet-section">
          <h4 class="section-label danger-label">Danger zone</h4>
          <div class="danger-zone">
            <div class="danger-row">
              <div>
                <strong>{{ user.disabled ? 'Enable account' : 'Disable account' }}</strong>
                <p>{{ user.disabled ? 'Allow this user to sign in again.' : 'Block sign-in and end all sessions. Reversible.' }}</p>
              </div>
              <button class="btn btn-sm" :class="user.disabled ? 'btn-secondary' : 'btn-danger-outline'" :disabled="busy"
                      @click="toggleStatus">
                {{ user.disabled ? 'Enable' : 'Disable' }}
              </button>
            </div>
            <div class="danger-row">
              <div>
                <strong>Delete user</strong>
                <p>Permanently remove the account and its data. This cannot be undone.</p>
              </div>
              <button class="btn btn-danger btn-sm" :disabled="busy" @click="deleteUser">Delete</button>
            </div>
          </div>
        </section>
      </template>
      <p v-else class="alert mt-md">
        <Lock :size="16" aria-hidden="true" />Only a root administrator can manage this account.
      </p>

      <div v-if="actionError" class="alert alert-error mt-md" role="alert">
        <CircleAlert :size="18" aria-hidden="true" />{{ actionError }}
      </div>
    </div>
  </AppSheet>
  <!-- Outside the sheet so closing the sheet can never strand it. -->
  <OneTimePasswordDialog :issued="issued" @close="issued = null" />
</template>

<script>
import { mapGetters, mapState } from 'vuex';
import { CircleAlert, KeyRound, Lock, Inbox, ChevronRight } from 'lucide-vue-next';
import api from '@/api';
import ErrorAlert from '@/components/ui/ErrorAlert.vue';
import AppSheet from '@/components/ui/AppSheet.vue';
import CopyButton from '@/components/ui/CopyButton.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import PasswordInput from '@/components/ui/PasswordInput.vue';
import OneTimePasswordDialog from '@/components/admin/OneTimePasswordDialog.vue';
import { refreshRequestCount } from '@/utils/adminRequests';
import { assetUrl } from '@/utils/url';
import { passwordError } from '@/utils/validation';
import { toast, confirmAction } from '@/utils/feedback';
import { dateTime, shortDate, roleBadge, relativeTime, toDate } from '@/utils/format';
import { providerName } from '@/utils/messages';

export default {
  name: 'UserDetailPane',
  components: {
    ErrorAlert, CircleAlert, KeyRound, Lock, Inbox, ChevronRight, AppSheet, CopyButton, StatusBadge, PasswordInput, OneTimePasswordDialog,
  },
  props: {
    open: Boolean,
    userId: { type: String, default: null },
  },
  emits: ['close', 'updated'],
  data() {
    return {
      user: null,
      loading: false,
      loadError: '',
      busy: false,
      selectedRole: 'user',
      showReset: false,
      requireChange: true,
      issued: null,
      newPassword: '',
      passwordProblem: '',
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
    fullName() {
      const p = this.user?.profile;
      return p ? [p.given_name, p.family_name].filter(Boolean).join(' ') : '';
    },
    shortId() {
      const id = String(this.user?.id || '');
      return id.length > 13 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
    },
    profileRows() {
      const p = this.user?.profile;
      if (!p) return [];
      const place = [p.city, p.state, p.country].filter(Boolean).join(', ');
      return [
        { label: 'Nickname', value: p.nick_name },
        { label: 'Date of birth', value: p.date_of_birth && shortDate(p.date_of_birth) },
        { label: 'Mobile', value: p.mobile_number && `${p.mobile_number}${p.phone_verified ? ' (verified)' : ''}` },
        { label: 'Location', value: place },
      ].filter(row => row.value);
    },
  },
  watch: {
    userId: {
      handler(id) {
        if (id !== this.user?.id) this.user = null;
        this.resetState();
        if (id) this.loadUser(id);
      },
      immediate: true,
    },
  },
  methods: {
    dateTime,
    relativeTime,
    providerName,
    roleBadge,
    resetState() {
      this.issued = null;
      this.actionError = '';
      this.loadError = '';
      this.cancelReset();
    },
    async loadUser(id) {
      this.loading = true;
      this.loadError = '';
      try {
        this.user = await api.getAdminUserDetail(id);
        this.selectedRole = this.user.role;
      } catch (e) {
        this.user = null;
        this.loadError = e.message;
      } finally {
        this.loading = false;
      }
    },
    // Runs an admin action on user `id` (captured before any prompt, so leaving
    // the pane meanwhile cannot redirect it), then reports, refreshes the list
    // and reloads the user if still shown. Returns the API result, or null.
    async run(id, action, success, { reload = true } = {}) {
      this.actionError = '';
      this.busy = true;
      try {
        const result = await action(id);
        toast(typeof success === 'function' ? success(result) : success);
        this.$emit('updated');
        if (reload && id === this.userId) await this.loadUser(id);
        return result;
      } catch (e) {
        this.actionError = e.message;
        return null;
      } finally {
        this.busy = false;
      }
    },
    async changeRole() {
      const id = this.userId;
      const role = this.selectedRole;
      const ok = await confirmAction({
        title: `Change ${this.user.username}'s role to ${role}?`,
        message: 'Their permissions change immediately and they are signed out of every session.',
        confirmLabel: 'Change role',
      });
      if (!ok) return;
      await this.run(id, target => api.updateUserRole(target, role), `Role changed to ${role}`);
    },
    async toggleStatus() {
      const id = this.userId;
      const disabling = !this.user.disabled;
      const ok = await confirmAction({
        title: `${disabling ? 'Disable' : 'Enable'} ${this.user.username}?`,
        message: disabling
          ? 'They will be signed out everywhere and cannot sign in until re-enabled.'
          : 'They will be able to sign in again.',
        confirmLabel: disabling ? 'Disable account' : 'Enable account',
        danger: disabling,
      });
      if (!ok) return;
      await this.run(id, api.toggleUserStatus, res => res.message);
    },
    async deleteUser() {
      const id = this.userId;
      const name = this.user.username;
      const ok = await confirmAction({
        title: `Delete ${name}?`,
        message: 'The account, profile and sessions are permanently removed. This cannot be undone.',
        confirmLabel: 'Delete user',
        danger: true,
        requireText: name,
      });
      if (!ok) return;
      if (await this.run(id, api.adminDeleteUser, `${name} was deleted`, { reload: false })) {
        this.$emit('close');
      }
    },
    async resetPassword() {
      this.passwordProblem = passwordError(this.newPassword);
      if (this.passwordProblem) return;
      const id = this.userId;
      const request = { newPassword: this.newPassword, requirePasswordChange: this.requireChange };
      const ok = await confirmAction({
        title: `Set a new password for ${this.user.username}?`,
        message: 'Their current password stops working and every session is signed out.',
        confirmLabel: 'Set password',
      });
      if (!ok) return;
      if (await this.run(id, target => api.adminResetPassword(target, request), res => res.message)) {
        this.cancelReset();
        refreshRequestCount();
      }
    },
    async generatePassword() {
      const id = this.userId;
      const ok = await confirmAction({
        title: `Generate a one-time password for ${this.user.username}?`,
        message: 'Their current password stops working and every session is signed out. They choose a new password at sign-in.',
        confirmLabel: 'Generate password',
      });
      if (!ok) return;
      const result = await this.run(id, target => api.adminResetPassword(target, { generate: true }),
        'One-time password generated');
      // Shown only if the admin is still looking at this user.
      if (result && id === this.userId) this.issued = result;
      if (result) refreshRequestCount();
    },
    expiresIn(value) {
      const hours = Math.round((toDate(value) - Date.now()) / 3600000);
      if (hours <= 0) return 'expired';
      return hours < 48 ? `expires in ${hours}h` : `expires in ${Math.round(hours / 24)}d`;
    },
    cancelReset() {
      this.showReset = false;
      this.requireChange = true;
      this.newPassword = '';
      this.passwordProblem = '';
    },
  },
};
</script>

<style scoped>
.role-picker { width: 100%; }
.role-picker button { flex: 1; }

.danger-label { color: var(--danger); }

.pending { margin-bottom: var(--space-md); text-decoration: none; align-items: center; }
.pending:hover { filter: brightness(1.05); }
.manual { margin-top: var(--space-sm); padding-top: var(--space-md); border-top: 1px solid var(--border); }

.danger-zone {
  border: 1px solid color-mix(in srgb, var(--danger) 35%, transparent);
  border-radius: var(--radius-lg);
}

.danger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-md);
}

.danger-row + .danger-row { border-top: 1px solid color-mix(in srgb, var(--danger) 20%, transparent); }
.danger-row strong { font-size: var(--text-md); font-weight: 600; }
.danger-row p { font-size: var(--text-sm); color: var(--text-muted); margin-top: 2px; }
</style>
