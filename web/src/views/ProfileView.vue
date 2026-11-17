<template>
  <div class="page-container narrow">
    <div v-if="loading" class="stack" aria-busy="true">
      <div class="card row" style="gap: 16px;">
        <span class="skeleton" style="width: 72px; height: 72px; border-radius: 50%;"></span>
        <div class="stack-sm spacer">
          <span class="skeleton" style="height: 18px; width: 45%;"></span>
          <span class="skeleton" style="height: 12px; width: 65%;"></span>
        </div>
      </div>
      <span class="skeleton" style="height: 220px; border-radius: 12px;"></span>
    </div>

    <template v-else>
      <!-- Identity -->
      <section class="card identity-card">
        <div class="identity">
          <button type="button" class="avatar-button" :aria-label="avatar ? 'Change profile photo' : 'Add profile photo'"
                  :disabled="!hasProfile || uploading" @click="triggerUpload">
            <img v-if="avatar" :src="avatar" class="avatar avatar-xl" alt="" referrerpolicy="no-referrer" />
            <span v-else class="avatar avatar-xl avatar-placeholder">{{ initials }}</span>
            <span v-if="hasProfile" class="avatar-badge" aria-hidden="true">
              <span v-if="uploading" class="spinner"></span>
              <Camera v-else :size="14" />
            </span>
          </button>
          <input ref="fileInput" type="file" accept="image/*" class="sr-only" tabindex="-1" aria-hidden="true"
                 @change="handleUpload" />
          <div class="wrap-anywhere">
            <h1>{{ displayName }}</h1>
            <p class="text-muted">{{ user?.email }}</p>
            <div class="badge-row mt-sm">
              <span class="badge">{{ user?.is_native ? 'Password account' : `${providerName(user?.auth_provider || '')} account` }}</span>
              <span v-if="user" class="badge" :class="user.email_verified ? 'badge-success' : 'badge-warning'">
                {{ user.email_verified ? 'Email verified' : 'Email unverified' }}
              </span>
            </div>
          </div>
        </div>
        <div v-if="pageError" class="alert alert-error mt-md" role="alert">
          <CircleAlert :size="18" aria-hidden="true" /><span>{{ pageError }}</span>
        </div>
      </section>

      <!-- No profile yet -->
      <section v-if="!hasProfile" class="card setup-card">
        <div>
          <h2>Finish setting up your profile</h2>
          <p class="text-muted text-md mt-xs">Add your name and details so connected apps can greet you properly.</p>
        </div>
        <router-link to="/profile/create" class="btn btn-primary">Set up profile</router-link>
      </section>

      <!-- Personal info -->
      <section v-else class="card">
        <div class="card-header section-head">
          <div>
            <h2>Personal info</h2>
            <p>Shared with apps only when you allow it.</p>
          </div>
          <button v-if="!editing" class="btn btn-secondary btn-sm" @click="startEditing">
            <Pencil :size="15" aria-hidden="true" />Edit
          </button>
        </div>

        <dl v-if="!editing" class="dl">
          <div class="dl-row"><dt>Name</dt><dd>{{ [profile.given_name, profile.family_name].filter(Boolean).join(' ') || '—' }}</dd></div>
          <div class="dl-row"><dt>Username</dt><dd>{{ user?.username }}</dd></div>
          <div class="dl-row" v-if="profile.nick_name"><dt>Nickname</dt><dd>{{ profile.nick_name }}</dd></div>
          <div class="dl-row" v-if="profile.date_of_birth"><dt>Date of birth</dt><dd>{{ shortDate(profile.date_of_birth) }}</dd></div>
          <div class="dl-row" v-if="profile.mobile_number"><dt>Mobile</dt><dd>{{ profile.mobile_number }}</dd></div>
          <div class="dl-row" v-if="formatAddress"><dt>Address</dt><dd>{{ formatAddress }}</dd></div>
        </dl>

        <form v-else class="stack" novalidate @submit.prevent="handleUpdate">
          <ProfileFields v-model="form" />
          <div v-if="editError" class="alert alert-error" role="alert">
            <CircleAlert :size="18" aria-hidden="true" /><span>{{ editError }}</span>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="editing = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="spinner" aria-hidden="true"></span>Save changes
            </button>
          </div>
        </form>
      </section>

      <!-- Sign-in & security -->
      <section class="card">
        <div class="card-header">
          <h2>Sign-in &amp; security</h2>
          <p>Changes need your current password{{ user?.is_native ? '' : ' (or a recent sign-in, if you never set one)' }}.</p>
        </div>

        <div class="setting-row">
          <div class="setting-icon" aria-hidden="true"><KeyRound :size="18" /></div>
          <div class="spacer">
            <strong>Password</strong>
            <p>{{ user?.is_native ? 'Used to sign in with your username.' : 'Optional. Lets you sign in without a provider.' }}</p>
          </div>
          <button v-if="openPanel !== 'password'" class="btn btn-secondary btn-sm" @click="openPanel = 'password'">Change</button>
        </div>
        <form v-if="openPanel === 'password'" class="panel stack" novalidate @submit.prevent="handlePasswordChange">
          <div class="form-group">
            <label for="current-password">Current password</label>
            <PasswordInput id="current-password" v-model="pw.current" autocomplete="current-password"
                           :required="user?.is_native" describedby="current-password-hint" />
            <p v-if="!user?.is_native" id="current-password-hint" class="form-hint">Leave empty if you never set one.</p>
          </div>
          <div class="form-group">
            <label for="new-password">New password</label>
            <PasswordInput id="new-password" v-model="pw.next" autocomplete="new-password" required
                           describedby="new-password-hint" />
            <p id="new-password-hint" class="form-hint">12+ characters with upper and lower case, a number and a symbol.</p>
          </div>
          <div class="form-group">
            <label for="confirm-password">Confirm new password</label>
            <PasswordInput id="confirm-password" v-model="pw.confirm" autocomplete="new-password" required />
          </div>
          <div v-if="pw.error" class="alert alert-error" role="alert"><CircleAlert :size="18" aria-hidden="true" /><span>{{ pw.error }}</span></div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="closePanel">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="pw.saving">Update password</button>
          </div>
        </form>

        <div class="setting-row">
          <div class="setting-icon" aria-hidden="true"><Mail :size="18" /></div>
          <div class="spacer wrap-anywhere">
            <strong>Email</strong>
            <p>{{ user?.email }}</p>
          </div>
          <button v-if="openPanel !== 'email'" class="btn btn-secondary btn-sm" @click="openPanel = 'email'">Change</button>
        </div>
        <form v-if="openPanel === 'email'" class="panel stack" @submit.prevent="handleEmailChange">
          <div class="form-group">
            <label for="new-email">New email</label>
            <input v-model="mail.email" id="new-email" type="email" inputmode="email" class="form-input"
                   autocomplete="email" autocapitalize="none" required />
          </div>
          <div class="form-group">
            <label for="email-password">Current password</label>
            <PasswordInput id="email-password" v-model="mail.current" autocomplete="current-password"
                           :required="user?.is_native" />
          </div>
          <div v-if="mail.error" class="alert alert-error" role="alert"><CircleAlert :size="18" aria-hidden="true" /><span>{{ mail.error }}</span></div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="closePanel">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="mail.saving">Update email</button>
          </div>
        </form>

        <router-link to="/sessions" class="setting-row setting-link">
          <div class="setting-icon" aria-hidden="true"><MonitorSmartphone :size="18" /></div>
          <div class="spacer">
            <strong>Devices &amp; sessions</strong>
            <p>See where you're signed in and sign out remotely.</p>
          </div>
          <ChevronRight :size="18" class="list-row-chevron" aria-hidden="true" />
        </router-link>
      </section>

      <!-- Linked accounts -->
      <section class="card">
        <div class="card-header">
          <h2>Linked accounts</h2>
          <p>Sign in with any of these providers.</p>
        </div>
        <div v-for="lp in linkedProviders" :key="lp.provider" class="setting-row">
          <div class="setting-icon" aria-hidden="true"><SSOIcon :provider="lp.provider" /></div>
          <div class="spacer wrap-anywhere">
            <strong>{{ providerName(lp.provider) }}</strong>
            <p>{{ lp.provider_email || lp.provider_username || 'Connected' }}</p>
          </div>
          <button class="btn btn-ghost btn-sm" @click="handleUnlink(lp.provider)">Unlink</button>
        </div>
        <p v-if="!linkedProviders.length" class="text-muted text-md">No providers linked yet.</p>

        <div v-if="availableToLink.length" class="link-list">
          <button v-for="p in availableToLink" :key="p" type="button" class="btn-sso" @click="linkProvider(p)">
            <SSOIcon :provider="p" aria-hidden="true" />
            Link {{ providerName(p) }}
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<script>
import { mapGetters, mapActions, mapState } from 'vuex';
import { Camera, CircleAlert, Pencil, KeyRound, Mail, MonitorSmartphone, ChevronRight } from 'lucide-vue-next';
import api from '@/api';
import SSOIcon from '@/components/SSOIcon.vue';
import ProfileFields, { PROFILE_FIELDS } from '@/components/ProfileFields.vue';
import PasswordInput from '@/components/ui/PasswordInput.vue';
import { assetUrl } from '@/utils/url';
import { passwordError, withoutEmpty } from '@/utils/validation';
import { providerName } from '@/utils/messages';
import { shortDate } from '@/utils/format';
import { toast, confirmAction } from '@/utils/feedback';

export default {
  name: 'ProfileView',
  components: {
    Camera, CircleAlert, Pencil, KeyRound, Mail, MonitorSmartphone, ChevronRight,
    SSOIcon, ProfileFields, PasswordInput,
  },
  data() {
    return {
      loading: true,
      editing: false,
      saving: false,
      uploading: false,
      editError: '',
      pageError: '',
      form: {},
      linkedProviders: [],
      openPanel: null,
      pw: { current: '', next: '', confirm: '', error: '', saving: false },
      mail: { email: '', current: '', error: '', saving: false },
    };
  },
  computed: {
    ...mapGetters(['hasProfile', 'initials', 'userProfile', 'currentUser']),
    ...mapState(['ssoProviders']),
    profile() { return this.userProfile || {}; },
    user() { return this.currentUser; },
    avatar() { return assetUrl(this.profile.picture); },
    displayName() {
      const name = [this.profile.given_name, this.profile.family_name].filter(Boolean).join(' ');
      return name || this.user?.username || 'Your account';
    },
    formatAddress() {
      const p = this.profile;
      const parts = [p.address_line1, p.address_line2, p.city, p.state, p.zip_code, p.country].filter(Boolean);
      return parts.join(', ');
    },
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
      toast(`${providerName(linked)} is now linked to your account.`);
      this.$router.replace({ path: '/profile' });
    }
  },
  methods: {
    ...mapActions(['updateProfile', 'uploadPicture']),
    providerName,
    shortDate,
    startEditing() {
      this.form = Object.fromEntries(PROFILE_FIELDS.map(key => [key, this.profile[key] || '']));
      this.editError = '';
      this.editing = true;
    },
    async handleUpdate() {
      this.editError = '';
      this.saving = true;
      try {
        await this.updateProfile(withoutEmpty(this.form));
        this.editing = false;
        toast('Profile updated');
      } catch (e) {
        this.editError = e.message;
      } finally {
        this.saving = false;
      }
    },
    triggerUpload() { this.$refs.fileInput.click(); },
    async handleUpload(e) {
      const file = e.target.files[0];
      e.target.value = '';
      if (!file) return;
      this.pageError = '';
      this.uploading = true;
      try {
        await this.uploadPicture(file);
        toast('Profile photo updated');
      } catch (err) {
        this.pageError = err.message;
      } finally {
        this.uploading = false;
      }
    },
    async loadLinked() {
      try {
        const data = await api.getLinkedProviders();
        this.linkedProviders = data.linked_providers || [];
      } catch { this.linkedProviders = []; }
    },
    async handleUnlink(provider) {
      const name = providerName(provider);
      const ok = await confirmAction({
        title: `Unlink ${name}?`,
        message: `You won't be able to sign in with ${name} until you link it again.`,
        confirmLabel: 'Unlink',
        danger: true,
      });
      if (!ok) return;
      try {
        await api.unlinkProvider(provider);
        await this.loadLinked();
        toast(`${name} unlinked`);
      } catch (e) { this.pageError = e.message; }
    },
    async linkProvider(provider) {
      try {
        // The API returns the provider URL; the browser comes back via /sso/callback.
        const { authorization_url } = await api.ssoLink(provider);
        window.location.assign(authorization_url);
      } catch (e) { this.pageError = e.message; }
    },
    closePanel() {
      this.openPanel = null;
      Object.assign(this.pw, { current: '', next: '', confirm: '', error: '' });
      Object.assign(this.mail, { email: '', current: '', error: '' });
    },
    async handlePasswordChange() {
      const pw = this.pw;
      pw.error = passwordError(pw.next, pw.confirm);
      if (pw.error) return;
      pw.saving = true;
      try {
        toast((await api.changePassword(pw.current, pw.next)).message);
        this.closePanel();
      } catch (e) {
        pw.error = e.message;
      } finally {
        pw.saving = false;
      }
    },
    async handleEmailChange() {
      const mail = this.mail;
      mail.error = '';
      mail.saving = true;
      try {
        const body = { email: mail.email };
        if (mail.current) body.current_password = mail.current;
        const user = await api.updateUser(this.user.id, body);
        toast(user.email_change_pending ? `Check ${mail.email} for a link to confirm the change.` : 'Email updated');
        this.closePanel();
        await this.$store.dispatch('fetchMe');
      } catch (e) {
        mail.error = e.message;
      } finally {
        mail.saving = false;
      }
    },
  },
};
</script>

<style scoped>
.narrow { max-width: 720px; }

.identity { display: flex; gap: var(--space-md); align-items: center; }
.identity h1 { font-size: var(--text-xl); }

@media (min-width: 768px) {
  .identity { gap: var(--space-lg); }
  .identity h1 { font-size: var(--text-2xl); }
}

.avatar-button {
  position: relative;
  border: none;
  background: none;
  padding: 0;
  border-radius: 50%;
  cursor: pointer;
  flex-shrink: 0;
}

.avatar-button:disabled { cursor: default; }

.avatar-badge {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  color: var(--text);
  box-shadow: var(--shadow-sm);
}

.setup-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.setup-card h2 { font-size: var(--text-lg); }

.section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-md); }

.setting-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid var(--border);
  color: var(--text);
  text-decoration: none;
}

.setting-row strong { font-size: var(--text-md); font-weight: 600; }
.setting-row p { font-size: var(--text-sm); color: var(--text-muted); margin-top: 1px; }
.setting-link:hover strong { text-decoration: underline; text-underline-offset: 3px; }

.setting-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-muted);
}

.setting-icon .sso-icon { width: 18px; height: 18px; }

.panel {
  padding: var(--space-md);
  margin-bottom: var(--space-md);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}

.form-actions { display: flex; gap: var(--space-sm); justify-content: flex-end; }

@media (max-width: 559px) {
  .form-actions .btn { flex: 1; }
}

.link-list { display: grid; gap: var(--space-sm); margin-top: var(--space-md); }

@media (min-width: 560px) {
  .link-list { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
}
</style>
