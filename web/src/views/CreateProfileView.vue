<template>
  <div class="page-center">
    <div class="auth-card card">
      <div class="auth-header">
        <div class="brand-mark">&gt;_</div>
        <h1>genesis<span class="accent">_profile</span></h1>
        <p class="text-muted">initialize your identity</p>
      </div>

      <form @submit.prevent="handleCreate" class="stack">
        <div class="row">
          <div class="form-group" style="flex:1">
            <label>First Name</label>
            <input v-model="form.given_name" class="form-input" placeholder="Jane" required />
          </div>
          <div class="form-group" style="flex:1">
            <label>Last Name</label>
            <input v-model="form.family_name" class="form-input" placeholder="Doe" required />
          </div>
        </div>
        <div class="form-group">
          <label>Nickname <span class="text-muted">(optional)</span></label>
          <input v-model="form.nick_name" class="form-input" placeholder="0xjdoe" />
        </div>
        <div class="row">
          <div class="form-group" style="flex:1">
            <label>Date of Birth</label>
            <input v-model="form.date_of_birth" type="date" class="form-input" />
          </div>
          <div class="form-group" style="flex:1">
            <label>Mobile</label>
            <input v-model="form.mobile_number" class="form-input" placeholder="+1 555 123 4567" />
          </div>
        </div>

        <div class="divider">address</div>

        <div class="form-group">
          <label>Address Line 1</label>
          <input v-model="form.address_line1" class="form-input" placeholder="123 Main St" />
        </div>
        <div class="form-group">
          <label>Address Line 2 <span class="text-muted">(optional)</span></label>
          <input v-model="form.address_line2" class="form-input" placeholder="Apt 4B" />
        </div>
        <div class="row">
          <div class="form-group" style="flex:1">
            <label>City</label>
            <input v-model="form.city" class="form-input" placeholder="New York" />
          </div>
          <div class="form-group" style="flex:1">
            <label>State</label>
            <input v-model="form.state" class="form-input" placeholder="NY" />
          </div>
        </div>
        <div class="row">
          <div class="form-group" style="flex:1">
            <label>Zip Code</label>
            <input v-model="form.zip_code" class="form-input" placeholder="10001" />
          </div>
          <div class="form-group" style="flex:1">
            <label>Country</label>
            <input v-model="form.country" class="form-input" placeholder="US" />
          </div>
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
      form: {
        given_name: '', family_name: '', nick_name: '',
        date_of_birth: '', mobile_number: '',
        address_line1: '', address_line2: '',
        city: '', state: '', zip_code: '', country: '',
      },
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
        const payload = { ...this.form, sub: username };
        // Remove empty optional fields
        Object.keys(payload).forEach(k => { if (payload[k] === '') delete payload[k]; });
        payload.given_name = this.form.given_name;
        payload.family_name = this.form.family_name;
        payload.sub = username;
        await this.createProfile(payload);
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
.auth-card { width: 100%; max-width: 500px; }

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
