/* Точка входа: маршруты, охрана по ролям, загрузка справочника и пользователя. */
import { createApp, defineComponent, onMounted, ref } from 'vue';
import { store, loadCatalog, loadMe, homeFor, logout, toast } from './store.js';
import { defineRoutes, startRouter, current, route, navigate } from './router.js';
import { components } from './ui.js';
import { AppShell } from './components/shell.js';
import { LoginPage, RegisterPage, ConfirmPage } from './components/auth.js';
import { CandidateOverview } from './components/candidate/overview.js';
import { CandidateProfile } from './components/candidate/profile.js';
import { CandidateSkills } from './components/candidate/skills.js';
import { CandidateTest } from './components/candidate/test.js';
import { TestHistory, TestSessionPage } from './components/candidate/test-history.js';
import { CandidateInvitations } from './components/candidate/invitations.js';
import { CandidateVacancies, CandidateVacancyPage, CandidateApplications } from './components/candidate/vacancies.js';
import { CandidateShortTasks } from './components/candidate/short-tasks.js';
import { CandidateAchievements } from './components/candidate/achievements.js';
import { CandidateSettings } from './components/candidate/settings.js';
import { EmployerOverview } from './components/employer/overview.js';
import { EmployerCompany } from './components/employer/company.js';
import { EmployerNeeds, EmployerNeedNew } from './components/employer/needs.js';
import { EmployerSelection } from './components/employer/selection.js';
import { EmployerBank } from './components/employer/bank.js';
import { EmployerInvitations } from './components/employer/invitations.js';
import { EmployerVacancies, EmployerVacancyForm, EmployerVacancyApplications } from './components/employer/vacancies.js';
import { EmployerShortTasks } from './components/employer/short-tasks.js';

const C = { role: 'candidate' };
const E = { role: 'employer' };
defineRoutes([
  { path: '/login', component: LoginPage, meta: { public: true, bare: true } },
  { path: '/register', component: RegisterPage, meta: { public: true, bare: true } },
  { path: '/confirm', component: ConfirmPage, meta: { public: true, bare: true } },

  { path: '/candidate', component: CandidateOverview, meta: C },
  { path: '/candidate/profile', component: CandidateProfile, meta: C },
  { path: '/candidate/skills', component: CandidateSkills, meta: C },
  { path: '/candidate/test', component: CandidateTest, meta: C },
  { path: '/candidate/test/history', component: TestHistory, meta: C },
  { path: '/candidate/test/sessions/:id', component: TestSessionPage, meta: C },
  { path: '/candidate/invitations', component: CandidateInvitations, meta: C },
  { path: '/candidate/invitations/:id', component: CandidateInvitations, meta: C },
  { path: '/candidate/vacancies', component: CandidateVacancies, meta: C },
  { path: '/candidate/vacancies/:id', component: CandidateVacancyPage, meta: C },
  { path: '/candidate/applications', component: CandidateApplications, meta: C },
  { path: '/candidate/tasks', component: CandidateShortTasks, meta: C },
  { path: '/candidate/achievements', component: CandidateAchievements, meta: C },
  { path: '/candidate/settings', component: CandidateSettings, meta: C },

  { path: '/employer', component: EmployerOverview, meta: E },
  { path: '/employer/company', component: EmployerCompany, meta: E },
  { path: '/employer/needs', component: EmployerNeeds, meta: E },
  { path: '/employer/needs/new', component: EmployerNeedNew, meta: E },
  { path: '/employer/selections/:id', component: EmployerSelection, meta: E },
  { path: '/employer/bank', component: EmployerBank, meta: E },
  { path: '/employer/invitations', component: EmployerInvitations, meta: E },
  { path: '/employer/vacancies', component: EmployerVacancies, meta: E },
  { path: '/employer/vacancies/new', component: EmployerVacancyForm, meta: E },
  { path: '/employer/vacancies/:id/edit', component: EmployerVacancyForm, meta: E },
  { path: '/employer/vacancies/:id/applications', component: EmployerVacancyApplications, meta: E },
  { path: '/employer/tasks', component: EmployerShortTasks, meta: E },
]);

function guard({ r, path }) {
  if (!r) return store.token ? homeFor(store.role) : '/login';
  const meta = r.meta || {};
  if (meta.public) {
    if (store.token && path !== '/confirm') return homeFor(store.role);
    return null;
  }
  if (!store.token) return '/login';
  if (meta.role && store.role && meta.role !== store.role) return homeFor(store.role);
  return null;
}

const App = defineComponent({
  components: { AppShell },
  setup() {
    const bootError = ref('');
    onMounted(async () => {
      try {
        await Promise.all([loadCatalog(), loadMe().catch((e) => { if (e.status === 401) return null; throw e; })]);
      } catch (e) {
        bootError.value = e.detail || e.message;
      } finally {
        store.ready = true;
        startRouter(guard);
      }
    });
    return { store, current, route, bootError, retry: () => location.reload() };
  },
  template: `
    <div v-if="!store.ready" class="boot"><span class="spinner"></span> Загрузка…</div>
    <div v-else-if="bootError" class="state state-error" style="padding:60px">
      <div><strong>Сервер недоступен.</strong> {{ bootError }}</div><button class="btn btn-outline" @click="retry">Повторить</button>
    </div>
    <template v-else-if="current">
      <component v-if="current.meta.bare" :is="current.component" :key="route.path" />
      <AppShell v-else><component :is="current.component" :key="route.path" /></AppShell>
    </template>`,
});

const app = createApp(App);
Object.entries(components).forEach(([name, comp]) => app.component(name, comp));
app.config.errorHandler = (err) => { console.error(err); toast(`Ошибка интерфейса: ${err.message || err}`, 'err'); };
app.mount('#app');
