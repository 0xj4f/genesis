<template>
  <div class="page-center">
    <div class="auth-card card">
      <div class="auth-header">
        <div class="brand-mark">&gt;_</div>
        <h1>genesis<span class="accent">_profile</span></h1>
        <p class="text-muted">initialize your identity</p>
      </div>

      <form @submit.prevent="handleCreate" class="stack">
        <div class="form-group">
          <label for="given_name">First Name</label>
          <input v-model="form.given_name" id="given_name" class="form-input"
                 placeholder="Jane" required />
        </div>
        <div class="form-group">
          <label for="family_name">Last Name</label>
          <input v-model="form.family_name" id="family_name" class="form-input"
                 placeholder="Doe" required />
        </div>
        <div class="form-group">
          <label for="nick_name">Handle <span class="text-muted">(optional)</span></label>
          <input v-model="form.nick_name" id="nick_name" class="form-input"
                 placeholder="0xjdoe" />
        </div>
        <div class="form-group">
          <label for="locale">Locale <span class="text-muted">(optional)</span></label>
          <input v-model="form.locale" id="locale" class="form-input"
                 placeholder="en-US" />
        </div>
        <div class="form-group">
          <label for="timezone">Timezone <span class="text-muted">(optional)</span></label>
          <input v-model="form.timezone" id="timezone" class="form-input"
                 placeholder="America/New_York" />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Initialize Profile</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

export default {
  name: 'CreateProfileView',
  data() {
    return {
      form: { given_name: '', family_name: '', nick_name: '', locale: '', timezone: '' },
      error: '',
      loading: false,
    };
  },
  computed: {
    ...mapGetters(['currentUser']),
  },
  methods: {
    ...mapActions(['createProfile']),
    async handleCreate() {
      this.error = '';
      this.loading = true;
      try {
        const username = this.currentUser?.username || 'user';
        await this.createProfile({ ...this.form, sub: username });
        this.$router.push('/profile');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.auth-card { width: 100%; max-width: 440px; }

.auth-header {
  text-align: center;
  margin-bottom: var(--space-xl);
}

.auth-header h1 {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin-top: var(--space-md);
}

.accent { color: var(--accent); }

.brand-mark {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  background: var(--bg-elevated);
  border: 1px solid var(--border-accent);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-xl);
  font-family: var(--font-mono);
}
</style>
