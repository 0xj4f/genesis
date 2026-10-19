<template>
  <div class="page-container">
    <!-- Loading -->
    <div v-if="loading" class="page-center">
      <div class="spinner" style="width: 32px; height: 32px;"></div>
    </div>

    <template v-else>
      <div class="profile-layout">
        <!-- No profile yet: account security and linking still apply -->
        <div v-if="!hasProfile" class="card text-center">
          <h2>Complete your profile</h2>
          <p class="text-muted mt-sm">You haven't set up your profile yet.</p>
          <router-link to="/profile/create" class="btn btn-primary btn-lg mt-lg" style="display:inline-flex;">
            Set Up Profile
          </router-link>
          <div v-if="linkedMsg" class="alert alert-success mt-md">{{ linkedMsg }}</div>
        </div>

        <!-- Profile Card -->
        <div v-else class="card profile-card">
          <div class="profile-top">
            <div class="avatar-section">
              <div v-if="avatar" class="avatar-wrap">
                <img :src="avatar" class="avatar avatar-lg" alt="Avatar" referrerpolicy="no-referrer" />
                <button class="avatar-edit btn btn-ghost btn-sm" @click="triggerUpload">Change</button>
              </div>
              <div v-else class="avatar avatar-lg avatar-placeholder" @click="triggerUpload"
                   style="cursor: pointer;" :title="'Upload a photo'">
                {{ initials }}
              </div>
              <input ref="fileInput" type="file" accept="image/*" style="display: none;" @change="handleUpload" />
            </div>
            <div class="profile-info">
              <h2>{{ profile.given_name }} {{ profile.family_name }}</h2>
              <p class="text-muted">{{ profile.email }}</p>
              <div class="badge-row mt-sm">
                <span class="badge" v-if="user">{{ user.auth_provider }}</span>
                <span class="badge badge-success" v-if="user && user.email_verified">verified</span>
                <span class="badge badge-danger" v-else>unverified</span>
              </div>
            </div>
          </div>

          <div v-if="uploadMsg" class="alert alert-success mt-md">{{ uploadMsg }}</div>
          <div v-if="linkedMsg" class="alert alert-success mt-md">{{ linkedMsg }}</div>

          <!-- Profile details -->
          <div class="profile-details mt-lg">
            <div class="detail-row">
              <span class="detail-label">Username</span>
              <span class="detail-value">{{ user?.username }}</span>
            </div>
            <div class="detail-row" v-if="profile.nick_name">
              <span class="detail-label">Nickname</span>
              <span class="detail-value">{{ profile.nick_name }}</span>
            </div>
            <div class="detail-row" v-if="profile.date_of_birth">
              <span class="detail-label">Date of Birth</span>
              <span class="detail-value">{{ profile.date_of_birth }}</span>
            </div>
            <div class="detail-row" v-if="profile.mobile_number">
              <span class="detail-label">Mobile</span>
              <span class="detail-value">{{ profile.mobile_number }}</span>
            </div>
            <div class="detail-row" v-if="profile.address_line1">
              <span class="detail-label">Address</span>
              <span class="detail-value">{{ formatAddress }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Account type</span>
              <span class="detail-value">{{ user?.is_native ? 'Native (password)' : 'SSO' }}</span>
            </div>
            <div class="detail-row" v-if="user?.last_login_at">
              <span class="detail-label">Last login</span>
              <span class="detail-value">{{ formatDate(user.last_login_at) }} via {{ user.last_login_method }}</span>
            </div>
          </div>

          <!-- Edit form toggle -->
          <div class="mt-lg">
            <button v-if="!editing" class="btn btn-secondary btn-block" @click="startEditing">
              Edit Profile
            </button>
            <form v-else @submit.prevent="handleUpdate" class="stack mt-md">
              <div class="form-group">
                <label>First Name</label>
                <input v-model="form.given_name" class="form-input" />
              </div>
              <div class="form-group">
                <label>Last Name</label>
                <input v-model="form.family_name" class="form-input" />
              </div>
              <div class="form-group">
                <label>Nickname</label>
                <input v-model="form.nick_name" class="form-input" placeholder="Optional" />
              </div>
              <div class="form-group">
                <label>Date of Birth</label>
                <input v-model="form.date_of_birth" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label>Mobile Number</label>
                <input v-model="form.mobile_number" class="form-input" placeholder="+1 555 123 4567" />
              </div>
              <div class="form-group">
                <label>Address</label>
                <input v-model="form.address_line1" class="form-input" placeholder="Street address" />
              </div>
              <div class="form-group">
                <label>Address Line 2</label>
                <input v-model="form.address_line2" class="form-input" placeholder="Apt, suite, unit" />
              </div>
              <div class="row">
                <div class="form-group" style="flex:1">
                  <label>City</label>
                  <input v-model="form.city" class="form-input" />
                </div>
                <div class="form-group" style="flex:1">
                  <label>State</label>
                  <input v-model="form.state" class="form-input" />
                </div>
              </div>
              <div class="row">
                <div class="form-group" style="flex:1">
                  <label>Zip Code</label>
                  <input v-model="form.zip_code" class="form-input" />
                </div>
                <div class="form-group" style="flex:1">
                  <label>Country</label>
                  <input v-model="form.country" class="form-input" />
                </div>
              </div>
              <div v-if="editError" class="alert alert-error">{{ editError }}</div>
              <div class="row">
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  <span v-if="saving" class="spinner"></span>
                  <span v-else>Save</span>
                </button>
                <button type="button" class="btn btn-secondary" @click="editing = false">Cancel</button>
              </div>
            </form>
          </div>
        </div>

        <!-- Account Security Card -->
        <div class="card">
          <div class="card-header">
            <h2>Account Security</h2>
            <p>Changes need your current password (or a recent sign-in for SSO-only accounts).</p>
          </div>

          <form @submit.prevent="handlePasswordChange" class="stack">
            <h3 class="text-sm">Change password</h3>
            <div class="form-group">
              <label for="current-password">Current password</label>
              <input v-model="pw.current" id="current-password" type="password" class="form-input"
                     autocomplete="current-password" :required="user?.is_native"
                     :placeholder="user?.is_native ? '' : 'leave empty if you never set one'" />
            </div>
            <div class="form-group">
              <label for="new-password">New password</label>
              <input v-model="pw.next" id="new-password" type="password" class="form-input"
                     autocomplete="new-password" minlength="12" maxlength="128" required />
            </div>
            <div class="form-group">
              <label for="confirm-password">Confirm new password</label>
              <input v-model="pw.confirm" id="confirm-password" type="password" class="form-input"
                     autocomplete="new-password" required />
            </div>
            <div v-if="pw.error" class="alert alert-error">{{ pw.error }}</div>
            <div v-if="pw.msg" class="alert alert-success">{{ pw.msg }}</div>
            <button type="submit" class="btn btn-secondary" :disabled="pw.saving">Update password</button>
          </form>

          <form @submit.prevent="handleEmailChange" class="stack mt-lg">
            <h3 class="text-sm">Change email</h3>
            <div class="form-group">
              <label for="new-email">New email</label>
              <input v-model="mail.email" id="new-email" type="email" class="form-input" autocomplete="email" required />
            </div>
            <div class="form-group">
              <label for="email-password">Current password</label>
              <input v-model="mail.current" id="email-password" type="password" class="form-input"
                     autocomplete="current-password" :required="user?.is_native" />
            </div>
            <div v-if="mail.error" class="alert alert-error">{{ mail.error }}</div>
            <div v-if="mail.msg" class="alert alert-success">{{ mail.msg }}</div>
            <button type="submit" class="btn btn-secondary" :disabled="mail.saving">Update email</button>
          </form>
        </div>

        <!-- Linked Accounts Card -->
        <div class="card">
          <div class="card-header">
            <h2>Linked Accounts</h2>
            <p>SSO providers connected to your account</p>
          </div>
          <div v-if="linkedProviders.length === 0" class="text-muted text-sm">
            No SSO providers linked yet.
          </div>
          <div v-for="lp in linkedProviders" :key="lp.provider" class="linked-row">
            <div class="row">
              <SSOIcon :provider="lp.provider" />
              <div>
                <strong>{{ capitalize(lp.provider) }}</strong>
                <span class="text-muted text-sm" v-if="lp.provider_email"> &middot; {{ lp.provider_email }}</span>
              </div>
            </div>
            <button class="btn btn-ghost btn-sm" @click="handleUnlink(lp.provider)">Unlink</button>
          </div>

          <div v-if="availableToLink.length" class="mt-md">
            <p class="text-sm text-muted mb-md">Link another provider:</p>
            <div class="stack">
              <button v-for="p in availableToLink" :key="p" type="button" class="btn-sso" @click="linkProvider(p)">
                <SSOIcon :provider="p" />
                Link {{ capitalize(p) }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { mapGetters, mapActions, mapState } from 'vuex';
import api from '@/api';
import SSOIcon from '@/components/SSOIcon.vue';
import { assetUrl } from '@/utils/url';
import { passwordError, withoutEmpty } from '@/utils/validation';

export default {
  name: 'ProfileView',
  components: { SSOIcon },
  data() {
    return {
      loading: true,
      editing: false,
      saving: false,
      editError: '',
      uploadMsg: '',
      form: {},
      linkedProviders: [],
      linkedMsg: '',
      pw: { current: '', next: '', confirm: '', error: '', msg: '', saving: false },
      mail: { email: '', current: '', error: '', msg: '', saving: false },
    };
  },
  computed: {
    ...mapGetters(['hasProfile', 'initials', 'userProfile', 'currentUser']),
    ...mapState(['ssoProviders']),
    profile() { return this.userProfile || {}; },
    avatar() { return assetUrl(this.profile.picture); },
    formatAddress() {
      const p = this.profile;
      const parts = [p.address_line1, p.address_line2, p.city, p.state, p.zip_code, p.country].filter(Boolean);
      return parts.join(', ');
    },
    user() { return this.currentUser; },
    availableToLink() {
      const linked = this.linkedProviders.map(l => l.provider);
      return this.ssoProviders.filter(p => !linked.includes(p));
    },
  },
  async created() {
    await Promise.all([
      this.$store.dispatch('fetchMe'),
      this.$store.dispatch('fetchProfile'),
      this.$store.dispatch('fetchSSOProviders'),
      this.loadLinked(),
    ]);
    this.loading = false;
    const linked = this.$route.query.linked;
    if (typeof linked === 'string') {
      this.linkedMsg = `${this.capitalize(linked)} is now linked to your account.`;
      this.$router.replace({ path: '/profile' });
    }
  },
  methods: {
    ...mapActions(['updateProfile', 'uploadPicture']),
    startEditing() {
      this.form = {
        given_name: this.profile.given_name || '',
        family_name: this.profile.family_name || '',
        nick_name: this.profile.nick_name || '',
        date_of_birth: this.profile.date_of_birth || '',
        mobile_number: this.profile.mobile_number || '',
        address_line1: this.profile.address_line1 || '',
        address_line2: this.profile.address_line2 || '',
        city: this.profile.city || '',
        state: this.profile.state || '',
        zip_code: this.profile.zip_code || '',
        country: this.profile.country || '',
      };
      this.editing = true;
    },
    async handleUpdate() {
      this.editError = '';
      this.saving = true;
      try {
        await this.updateProfile(withoutEmpty(this.form));
        this.editing = false;
      } catch (e) {
        this.editError = e.message;
      } finally {
        this.saving = false;
      }
    },
    triggerUpload() { this.$refs.fileInput.click(); },
    async handleUpload(e) {
      const file = e.target.files[0];
      if (!file) return;
      try {
        await this.uploadPicture(file);
        this.uploadMsg = 'Profile picture updated!';
        setTimeout(() => { this.uploadMsg = ''; }, 3000);
      } catch (err) { this.editError = err.message; }
    },
    async loadLinked() {
      try {
        const data = await api.getLinkedProviders();
        this.linkedProviders = data.linked_providers || [];
      } catch { this.linkedProviders = []; }
    },
    async handleUnlink(provider) {
      try {
        await api.unlinkProvider(provider);
        await this.loadLinked();
      } catch (e) { this.editError = e.message; }
    },
    async linkProvider(provider) {
      try {
        // The API returns the provider URL; the browser comes back via /sso/callback.
        const { authorization_url } = await api.ssoLink(provider);
        window.location.assign(authorization_url);
      } catch (e) { this.editError = e.message; }
    },
    async handlePasswordChange() {
      const pw = this.pw;
      pw.msg = '';
      pw.error = passwordError(pw.next, pw.confirm);
      if (pw.error) return;
      pw.saving = true;
      try {
        pw.msg = (await api.changePassword(pw.current, pw.next)).message;
        pw.current = pw.next = pw.confirm = '';
      } catch (e) {
        pw.error = e.message;
      } finally {
        pw.saving = false;
      }
    },
    async handleEmailChange() {
      const mail = this.mail;
      mail.msg = '';
      mail.error = '';
      mail.saving = true;
      try {
        const body = { email: mail.email };
        if (mail.current) body.current_password = mail.current;
        const user = await api.updateUser(this.user.id, body);
        mail.msg = user.email_change_pending
          ? `Check ${mail.email} for a link to confirm the change.`
          : 'Email updated.';
        mail.email = mail.current = '';
        await this.$store.dispatch('fetchMe');
      } catch (e) {
        mail.error = e.message;
      } finally {
        mail.saving = false;
      }
    },
    capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); },
    formatDate(d) { return d ? new Date(d).toLocaleString() : ''; },
  },
};
</script>

<style scoped>
.profile-layout {
  display: grid;
  gap: var(--space-lg);
  max-width: 700px;
  margin: 0 auto;
}

.profile-top {
  display: flex;
  gap: var(--space-xl);
  align-items: center;
}

.avatar-section { position: relative; }
.avatar-wrap { position: relative; }

.avatar-edit {
  position: absolute;
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--text-xs);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  padding: 2px 10px;
}

.profile-info h2 {
  font-size: var(--text-2xl);
  font-weight: 600;
}

.badge-row {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.profile-details {
  border-top: 1px solid var(--border-color);
  padding-top: var(--space-lg);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--bg-muted);
  font-size: var(--text-sm);
}

.detail-label { color: var(--text-secondary); font-weight: 500; }
.detail-value { color: var(--text-primary); }

.linked-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--bg-muted);
}

.linked-row:last-of-type { border-bottom: none; }
</style>
