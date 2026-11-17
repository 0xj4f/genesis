<template>
  <div ref="root" class="account">
    <button class="account-trigger" :aria-expanded="String(open)" aria-haspopup="menu"
            :aria-label="`Account menu for ${name}`" @click="open = !open">
      <img v-if="avatar" :src="avatar" class="avatar avatar-sm" alt="" referrerpolicy="no-referrer" />
      <span v-else class="avatar avatar-sm avatar-placeholder">{{ initials }}</span>
      <span v-if="badge" class="badge badge-warning account-badge">{{ badge }}</span>
    </button>
    <transition name="menu">
      <div v-if="open" class="menu" role="menu" @keydown.esc="close">
        <div class="menu-header">
          <div class="truncate"><strong>{{ name }}</strong></div>
          <div v-if="email" class="text-sm text-muted truncate">{{ email }}</div>
        </div>
        <div class="menu-theme">
          <span class="text-sm text-muted">Theme</span>
          <ThemeToggle />
        </div>
        <div class="menu-sep"></div>
        <slot />
        <button class="menu-item danger" role="menuitem" @click="signOut">
          <LogOut :size="16" aria-hidden="true" />Sign out
        </button>
      </div>
    </transition>
  </div>
</template>

<script>
import { LogOut } from 'lucide-vue-next';
import ThemeToggle from '@/components/ui/ThemeToggle.vue';

export default {
  name: 'AccountMenu',
  components: { LogOut, ThemeToggle },
  props: {
    name: { type: String, default: 'Account' },
    email: { type: String, default: '' },
    avatar: { type: String, default: '' },
    initials: { type: String, default: '?' },
    badge: { type: String, default: '' },
  },
  emits: ['sign-out'],
  data() {
    return { open: false };
  },
  watch: {
    '$route.fullPath'() { this.open = false; },
  },
  mounted() { document.addEventListener('pointerdown', this.onOutside); },
  beforeUnmount() { document.removeEventListener('pointerdown', this.onOutside); },
  methods: {
    onOutside(event) {
      if (this.open && !this.$refs.root.contains(event.target)) this.open = false;
    },
    close() { this.open = false; },
    signOut() {
      this.open = false;
      this.$emit('sign-out');
    },
  },
};
</script>

<style scoped>
.account { position: relative; }

.account-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 4px;
  border: none;
  background: none;
  border-radius: var(--radius-full);
  cursor: pointer;
}

.account-trigger:hover .avatar { box-shadow: 0 0 0 3px var(--surface-hover); }
.menu-theme { display: flex; align-items: center; justify-content: space-between; gap: var(--space-md); padding: 4px 10px; }

.menu-enter-active { transition: opacity 140ms ease, transform 140ms var(--ease-out); }
.menu-leave-active { transition: opacity 100ms ease; }
.menu-enter-from { opacity: 0; transform: translateY(-4px); }
.menu-leave-to { opacity: 0; }
</style>
