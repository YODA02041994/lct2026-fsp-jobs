/* Оболочка кабинета: шапка, навигация по роли, уведомления, окно подтверждения. */
import { computed } from 'vue';
import { store, logout, closeConfirm, refreshMe, toast } from '../store.js';
import { route, isActive } from '../router.js';
import { api } from '../api.js';

const CANDIDATE_NAV = [
  { to: '/candidate', title: 'Обзор', exact: true },
  { to: '/candidate/profile', title: 'Профиль' },
  { to: '/candidate/skills', title: 'Навыки' },
  { to: '/candidate/test', title: 'Тестирование' },
  { to: '/candidate/invitations', title: 'Приглашения', counter: 'invitations' },
  { to: '/candidate/vacancies', title: 'Вакансии', also: ['/candidate/applications'] },
  { to: '/candidate/tasks', title: 'Задания' },
  { to: '/candidate/achievements', title: 'Достижения ФСП' },
  { to: '/candidate/settings', title: 'Настройки' },
];
const EMPLOYER_NAV = [
  { to: '/employer', title: 'Обзор', exact: true },
  { to: '/employer/company', title: 'Компания' },
  { to: '/employer/needs', title: 'Потребности и подборки', also: ['/employer/selections'] },
  { to: '/employer/bank', title: 'Банк кандидатов' },
  { to: '/employer/invitations', title: 'Приглашения' },
  { to: '/employer/vacancies', title: 'Вакансии' },
  { to: '/employer/tasks', title: 'Короткие задания' },
];

export const AppShell = {
  setup() {
    const nav = computed(() => (store.role === 'employer' ? EMPLOYER_NAV : CANDIDATE_NAV));
    const roleTitle = computed(() => (store.role === 'employer' ? 'Работодатель' : 'Кандидат'));
    const counters = store.counters || (store.counters = { invitations: 0 });
    async function loadCounters() {
      if (store.role !== 'candidate') return;
      try {
        const list = await api.get('/candidates/me/invitations');
        counters.invitations = list.filter((i) => i.status === 'sent').length;
      } catch (_) { /* не критично */ }
    }
    loadCounters();
    window.addEventListener('fsp:invitations-changed', loadCounters);
    // возврат от издателя ФСП ID
    if (route.query.fsp === 'linked') {
      refreshMe().then(() => toast('ФСП ID связан с профилем. Достижения загружены', 'ok'));
    }
    function active(item) {
      if (item.exact) return route.path === item.to;
      return isActive(item.to) || (item.also || []).some((p) => isActive(p));
    }
    return { store, nav, roleTitle, counters, active, logout, closeConfirm };
  },
  template: `
    <header class="topbar">
      <div class="topbar-in">
        <a class="brand" :href="'#' + (store.role === 'employer' ? '/employer' : '/candidate')"><span class="brand-mark">К</span><span>Карьера ФСП</span></a>
        <span class="spacer"></span>
        <span class="role-pill">{{ roleTitle }}</span>
        <span class="user-email" :title="store.user && store.user.email">{{ store.user && store.user.email }}</span>
        <button type="button" class="btn-exit" @click="logout()">Выйти</button>
      </div>
    </header>
    <nav class="nav" aria-label="Разделы кабинета">
      <div class="nav-in">
        <a v-for="n in nav" :key="n.to" :href="'#' + n.to" :class="{ active: active(n) }">{{ n.title }}<span v-if="n.counter && counters[n.counter]" class="count">{{ counters[n.counter] }}</span></a>
      </div>
    </nav>
    <main class="main"><slot></slot></main>
    <Modal v-if="store.confirm" :title="store.confirm.title" @close="closeConfirm(false)">
      <p class="pre-wrap">{{ store.confirm.text }}</p>
      <template #footer>
        <button type="button" class="btn btn-ghost" @click="closeConfirm(false)">{{ store.confirm.cancel }}</button>
        <button type="button" class="btn" :class="store.confirm.danger ? 'btn-danger' : 'btn-primary'" @click="closeConfirm(true)">{{ store.confirm.ok }}</button>
      </template>
    </Modal>`,
};
