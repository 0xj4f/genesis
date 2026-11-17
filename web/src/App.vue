<template>
  <div id="app-root" :class="{ 'has-tabbar': showUserNav }">
    <a href="#main" class="skip-link">Skip to content</a>

    <!-- User app shell (admin pages bring their own layout) -->
    <header v-if="showUserNav" class="topbar">
      <div class="topbar-inner">
        <router-link to="/profile" class="brand">
          <BrandMark />
          <span>Genesis</span>
        </router-link>
        <nav class="topnav" aria-label="Main">
          <router-link to="/profile"><UserRound :size="16" aria-hidden="true" />Profile</router-link>
          <router-link to="/sessions"><MonitorSmartphone :size="16" aria-hidden="true" />Sessions</router-link>
        </nav>
        <div class="spacer"></div>
        <AccountMenu :name="displayName" :email="currentUser?.email" :avatar="avatar" :initials="initials"
                     @sign-out="logout" />
      </div>
    </header>

    <div id="main" tabindex="-1">
      <router-view />
    </div>

    <nav v-if="showUserNav" class="tabbar" aria-label="Main">
      <router-link to="/profile"><UserRound :size="22" aria-hidden="true" />Profile</router-link>
      <router-link to="/sessions"><MonitorSmartphone :size="22" aria-hidden="true" />Sessions</router-link>
    </nav>

    <ToastHost />
    <ConfirmDialog />
  </div>
</template>

<script>
import { mapGetters, mapActions, mapState } from 'vuex';
import { UserRound, MonitorSmartphone } from 'lucide-vue-next';
import BrandMark from '@/components/ui/BrandMark.vue';
import AccountMenu from '@/components/ui/AccountMenu.vue';
import ToastHost from '@/components/ui/ToastHost.vue';
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue';
import { assetUrl } from '@/utils/url';

export default {
  name: 'App',
  components: { UserRound, MonitorSmartphone, BrandMark, AccountMenu, ToastHost, ConfirmDialog },
  computed: {
    ...mapGetters(['isAuthenticated', 'currentUser', 'initials']),
    ...mapState(['profile']),
    showUserNav() {
      return this.isAuthenticated && !this.$route.path.startsWith('/admin') && !this.$route.meta.bare;
    },
    displayName() {
      if (this.profile?.given_name) return `${this.profile.given_name} ${this.profile.family_name || ''}`.trim();
      return this.currentUser?.username || 'Account';
    },
    avatar() { return assetUrl(this.profile?.picture); },
  },
  watch: {
    // Move focus to the new page for keyboard and screen reader users.
    '$route.path'(to, from) {
      if (from && to.split('/')[1] !== from.split('/')[1]) {
        this.$nextTick(() => document.getElementById('main')?.focus({ preventScroll: true }));
      }
    },
  },
  methods: {
    ...mapActions(['logout']),
  },
};
</script>

<style>
#main:focus { outline: none; }

.skip-link {
  position: absolute;
  left: var(--space-md);
  top: -100px;
  z-index: var(--z-toast);
  padding: 8px 12px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  color: var(--text);
}

.skip-link:focus { top: calc(var(--space-sm) + var(--safe-top)); }
</style>
