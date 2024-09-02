<template>
  <div class="login-view">
    <LoginForm />
  </div>
</template>

<script>
import LoginForm from '@/components/LoginForm.vue'; // Import the login form component

export default {
  name: 'LoginView',
  components: {
    LoginForm,
  },
};
</script>

<style scoped>
.login-view {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f0f0;
}
</style>
