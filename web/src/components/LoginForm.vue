<template>
  <div class="card">
    <h2>Login</h2>
    <form @submit.prevent="loginUser">
      <div class="form-group">
        <label for="username">Username:</label>
        <input v-model="username" type="text" id="username" required />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input v-model="password" type="password" id="password" required />
      </div>
      <button type="submit">Login</button>
    </form>

    <!-- Success Message -->
    <div v-if="successMessage" class="success-message">
      {{ successMessage }}
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginForm',
  data() {
    return {
      username: '',
      password: '',
      successMessage: '',
      errorMessage: ''
    };
  },
  methods: {
    async loginUser() {
      const formData = new URLSearchParams();
      formData.append('username', this.username);
      formData.append('password', this.password);

      try {
        const response = await fetch('http://127.0.0.1:8000/token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            Accept: 'application/json',
          },
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          console.log(result);
          this.successMessage = 'Login successful!';
          this.errorMessage = '';
          // Store tokens in localStorage or Vuex for further use
          localStorage.setItem('access_token', result.access_token);
          localStorage.setItem('refresh_token', result.refresh_token);
        } else {
          const errorResult = await response.json();
          this.errorMessage = errorResult.detail || 'Login failed. Please try again.';
          this.successMessage = '';
        }
      } catch (error) {
        console.error('Error:', error);
        this.errorMessage = 'An error occurred during login. Please try again.';
        this.successMessage = '';
      }
    },
  },
};
</script>

<style scoped>
.card {
  border-radius: 50px;
  background: #e0e0e0;
  box-shadow: 20px 20px 60px #bebebe, -20px -20px 60px #ffffff;
  padding: 30px;
  width: 300px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

input {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 5px;
  box-shadow: inset 5px 5px 10px #bebebe, inset -5px -5px 10px #ffffff;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  background-color: #e0e0e0;
  box-shadow: 5px 5px 10px #bebebe, -5px -5px 10px #ffffff;
  cursor: pointer;
}

button:hover {
  background-color: #d4d4d4;
}

.success-message {
  margin-top: 20px;
  padding: 10px;
  color: #28a745;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 5px;
}

.error-message {
  margin-top: 20px;
  padding: 10px;
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 5px;
}
</style>
