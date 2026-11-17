import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import store from './store';
import { initTheme } from './utils/theme';
import './assets/design.css';

initTheme();
createApp(App).use(store).use(router).mount('#app');
