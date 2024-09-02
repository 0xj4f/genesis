<template>
  <div v-if="userProfile" class="profile-card">
    <h2>User Profile</h2>
    <p><strong>Given Name:</strong> {{ userProfile.given_name }}</p>
    <p><strong>Family Name:</strong> {{ userProfile.family_name }}</p>
    <p><strong>Nickname:</strong> {{ userProfile.nick_name }}</p>
    <p><strong>Email:</strong> {{ userProfile.email }}</p>
    <!-- Add other profile details as needed -->
  </div>
  <div v-else>
    <p>Loading profile...</p>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'UserProfile',
  computed: {
    ...mapGetters(['userProfile']),
  },
  created() {
    if (!this.userProfile) {
      this.fetchUserProfile(); // Fetch user profile if not already loaded
    }
  },
  methods: {
    ...mapActions(['fetchUserProfile']),
  },
};
</script>

<style scoped>
.profile-card {
  border-radius: 20px;
  background: #e0e0e0;
  box-shadow: 10px 10px 20px #bebebe, -10px -10px 20px #ffffff;
  padding: 30px;
  width: 400px;
  text-align: center;
}
</style>
