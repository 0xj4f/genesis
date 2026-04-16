<template>
  <div class="page-container">
    <!-- Loading -->
    <div v-if="loading" class="page-center">
      <div class="spinner" style="width: 32px; height: 32px;"></div>
    </div>

    <!-- No profile -> redirect to create -->
    <template v-else-if="!hasProfile">
      <div class="card text-center" style="max-width: 500px; margin: var(--space-2xl) auto;">
        <h2>Complete your profile</h2>
        <p class="text-muted mt-sm">You haven't set up your profile yet.</p>
        <router-link to="/profile/create" class="btn btn-primary btn-lg mt-lg" style="display:inline-flex;">
          Set Up Profile
        </router-link>
      </div>
    </template>

    <!-- Profile view -->
    <template v-else>
      <div class="profile-layout">
        <!-- Profile Card -->
        <div class="card profile-card">
          <div class="profile-top">
            <div class="avatar-section">
              <div v-if="profile.picture" class="avatar-wrap">
                <img :src="fixUrl(profile.picture)" class="avatar avatar-lg" alt="Avatar" />
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
            <div class="detail-row" v-if="profile.locale">
              <span class="detail-label">Locale</span>
              <span class="detail-value">{{ profile.locale }}</span>
            </div>
            <div class="detail-row" v-if="profile.timezone">
              <span class="detail-label">Timezone</span>
              <span class="detail-value">{{ profile.timezone }}</span>
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
                <label>Locale</label>
                <input v-model="form.locale" class="form-input" placeholder="e.g. en-US" />
              </div>
              <div class="form-group">
                <label>Timezone</label>
                <input v-model="form.timezone" class="form-input" placeholder="e.g. America/New_York" />
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
              <a v-for="p in availableToLink" :key="p" :href="ssoLinkUrl(p)" class="btn-sso">
                <SSOIcon :provider="p" />
                Link {{ capitalize(p) }}
              </a>
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
    };
  },
  computed: {
    ...mapGetters(['hasProfile', 'initials', 'userProfile', 'currentUser']),
    ...mapState(['ssoProviders']),
    profile() { return this.userProfile || {}; },
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
  },
  methods: {
    ...mapActions(['updateProfile', 'uploadPicture']),
    startEditing() {
      this.form = {
        given_name: this.profile.given_name || '',
        family_name: this.profile.family_name || '',
        nick_name: this.profile.nick_name || '',
        locale: this.profile.locale || '',
        timezone: this.profile.timezone || '',
      };
      this.editing = true;
    },
    async handleUpdate() {
      this.editError = '';
      this.saving = true;
      try {
        await this.updateProfile(this.form);
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
        const data = await api.getLinkedProviders(this.$store.state.accessToken);
        this.linkedProviders = data.linked_providers || [];
      } catch { this.linkedProviders = []; }
    },
    async handleUnlink(provider) {
      try {
        await api.unlinkProvider(this.$store.state.accessToken, provider);
        await this.loadLinked();
      } catch (e) { this.editError = e.message; }
    },
    ssoLinkUrl(provider) { return api.ssoLinkUrl(provider); },
    capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); },
    fixUrl(url) {
      if (url && url.includes(':8000/')) return url.replace(':8000/', ':8001/');
      return url;
    },
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
