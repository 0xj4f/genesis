<template>
  <div class="card">
    <h2>Register</h2>
    <form @submit.prevent="registerUser">
      <div class="form-group">
        <label for="username">Username:</label>
        <input v-model="username" type="text" id="username" required />
      </div>
      <div class="form-group">
        <label for="email">Email:</label>
        <input v-model="email" type="email" id="email" required />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input v-model="password" type="password" id="password" required />
      </div>
      <button type="submit">Register</button>
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
  name: 'RegistrationForm',
  data() {
    return {
      username: '',
      email: '',
      password: '',
      successMessage: '',
      errorMessage: ''
    };
  },
  methods: {
    async registerUser() {
      const userData = {
        username: this.username,
        email: this.email,
        password: this.password,
      };
      try {
        const response = await fetch('http://127.0.0.1:8000/users/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: JSON.stringify(userData),
        });

        if (response.ok) {
          const result = await response.json();
          console.log(result);
          this.successMessage = 'Successfully registered!';
          this.errorMessage = '';
        } else {
          const errorResult = await response.json();
          if (errorResult.detail && errorResult.detail.length > 0) {
            this.errorMessage = errorResult.detail[0].msg;
          } else {
            this.errorMessage = 'Registration failed. Please try again.';
          }
          this.successMessage = '';
        }
      } catch (error) {
        console.error('Error:', error);
        this.errorMessage = 'An error occurred during registration. Please try again.';
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
