<!-- src/views/RegistrationView.vue -->

<template>
  <div class="registration-view">
    <RegistrationForm />
  </div>
</template>

<script>
import RegistrationForm from '@/components/RegistrationForm.vue';

export default {
  name: 'RegistrationView',
  components: {
    RegistrationForm
  }
};
</script>

<style scoped>
.registration-view {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f0f0;
}
</style>
