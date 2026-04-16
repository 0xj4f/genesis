<template>
  <div class="page-center">
    <div class="auth-card card admin-card">
      <div class="auth-header">
        <div class="brand-mark admin-mark">!</div>
        <h1>genesis<span class="warn">_admin</span></h1>
        <p class="text-muted">restricted access</p>
      </div>

      <form @submit.prevent="handleLogin" class="stack">
        <div class="form-group">
          <label for="username">Username</label>
          <input v-model="username" id="username" type="text" class="form-input"
                 placeholder="admin credentials" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input v-model="password" id="password" type="password" class="form-input"
                 placeholder="enter password" required />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <button type="submit" class="btn btn-admin btn-block btn-lg" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Access Console</span>
        </button>
      </form>

      <p class="text-center text-sm mt-lg text-muted">
        <router-link to="/login" class="link">Back to user login</router-link>
      </p>
    </div>
  </div>
</template>

<script>
import { mapActions } from 'vuex';

export default {
  name: 'AdminLoginView',
  data() {
    return { username: '', password: '', error: '', loading: false };
  },
  methods: {
    ...mapActions(['adminLogin']),
    async handleLogin() {
      this.error = '';
      this.loading = true;
      try {
        await this.adminLogin({ username: this.username, password: this.password });
        this.$router.push('/admin');
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
.auth-card { width: 100%; max-width: 420px; }

.admin-card::before { background: linear-gradient(135deg, #f59e0b, #d97706) !important; }

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

.warn { color: #f59e0b; }

.brand-mark {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-xl);
  font-family: var(--font-mono);
}

.admin-mark {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.btn-admin {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #0a0e17;
  font-weight: 700;
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.15);
}

.btn-admin:hover:not(:disabled) {
  box-shadow: 0 0 30px rgba(245, 158, 11, 0.25);
}
</style>
