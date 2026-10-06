/* Обзор кабинета работодателя. */
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, refreshMe } from '../../store.js';

export const EmployerOverview = {
  setup() {
    const needs = ref([]); const selections = ref([]); const invitations = ref([]); const vacancies = ref([]);
    const loading = ref(true); const error = ref('');
    onMounted(async () => {
      try {
        const [n, s, i, v] = await Promise.all([api.get('/needs'), api.get('/selections'), api.get('/employers/me/invitations'), api.get('/employers/me/vacancies'), refreshMe()]);
        needs.value = n; selections.value = s; invitations.value = i; vacancies.value = v;
      } catch (e) { error.value = e.detail; } finally { loading.value = false; }
    });
    const me = computed(() => store.me || {});
    const inv = computed(() => ({ total: invitations.value.length, open: invitations.value.filter((x) => ['sent', 'viewed'].includes(x.status)).length, accepted: invitations.value.filter((x) => x.status === 'accepted').length, declined: invitations.value.filter((x) => x.status === 'declined').length }));
    const steps = computed(() => [
      { done: !!(me.value.company_name && me.value.description), text: 'Заполнить профиль компании — его видит кандидат в приглашении', to: '/employer/company' },
      { done: needs.value.length > 0, text: 'Описать потребность: кто нужен, стек, грейд, зарплата', to: '/employer/needs/new' },
      { done: selections.value.length > 0, text: 'Собрать подборку и посмотреть обоснование по каждому кандидату', to: '/employer/needs' },
      { done: inv.value.total > 0, text: 'Отправить приглашение с зарплатой выбранному кандидату', to: '/employer/needs' },
      { done: inv.value.accepted > 0, text: 'Дождаться принятия — контакты откроются в разделе «Приглашения»', to: '/employer/invitations' },
    ]);
    return { me, needs, selections, inv, vacancies, steps, loading, error };
  },
  template: `
    <PageHead :title="me.company_name || 'Обзор'" sub="Обратная механика: вы описываете потребность, получаете подборку кандидатов по категориям с обоснованием и сами направляете приглашение с зарплатой. Контакты открываются после согласия кандидата.">
      <a href="#/employer/needs/new" class="btn btn-primary">Новая потребность</a>
    </PageHead>
    <div v-if="!loading && !me.company_name" class="note note-warn">Укажите название компании в <a href="#/employer/company">профиле</a> — кандидаты видят его в приглашении.</div>
    <div class="grid grid-4">
      <a class="stat accent" href="#/employer/needs"><div class="stat-label">Потребности и подборки</div><div class="stat-value">{{ needs.length }}</div><div class="stat-sub">подборок собрано: {{ selections.length }}</div></a>
      <a class="stat" href="#/employer/invitations"><div class="stat-label">Приглашения</div><div class="stat-value">{{ inv.total }}</div><div class="stat-sub">ждут ответа {{ inv.open }} · принято {{ inv.accepted }} · отклонено {{ inv.declined }}</div></a>
      <a class="stat" href="#/employer/invitations"><div class="stat-label">Контакты открыты</div><div class="stat-value">{{ inv.accepted }}</div><div class="stat-sub">кандидаты, принявшие приглашение</div></a>
      <a class="stat" href="#/employer/vacancies"><div class="stat-label">Вакансии</div><div class="stat-value">{{ vacancies.length }}</div><div class="stat-sub">отклики — в карточке вакансии</div></a>
    </div>
    <div class="grid grid-2" style="margin-top:14px">
      <div class="card"><h2>Что дальше</h2>
        <ul class="todo"><li v-for="s in steps" :key="s.text" :class="{ done: s.done }"><span class="mark">{{ s.done ? '✓' : '' }}</span><span class="text"><a v-if="!s.done" :href="'#' + s.to">{{ s.text }}</a><template v-else>{{ s.text }}</template></span></li></ul>
      </div>
      <div class="card"><h2>Как строится подборка</h2>
        <p>Кандидаты разложены по категориям «специализация × грейд», которые присвоены <strong>тестом</strong>, а не самоописанием. Внутри категории порядок задаёт оценка из шести слагаемых: стек (подтверждённые тестом технологии весят больше), грейд, сила подтверждённого профиля, достижения ФСП, актуальность, условия.</p>
        <p class="muted" style="margin:0">У каждого кандидата есть строка обоснования. Уточнение фильтров создаёт новую версию подборки — прежние не теряются.</p>
      </div>
    </div>`,
};
