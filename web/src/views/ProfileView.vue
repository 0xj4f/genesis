<template>
  <div class="profile-view">
    <UserProfile />
  </div>
</template>

<script>
import UserProfile from '@/components/UserProfile.vue'; // Import the user profile component

export default {
  name: 'ProfileView',
  components: {
    UserProfile,
  },
};
</script>

<style scoped>
.profile-view {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f0f0;
}
</style>
