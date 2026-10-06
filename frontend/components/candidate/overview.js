/* Обзор кабинета кандидата: категория, тест, приглашения, подсказки «что дальше». */
import { computed, onMounted, ref } from 'vue';
import { api } from '../../api.js';
import { store, refreshMe, categoryTitle, gradeTitle, specName } from '../../store.js';
import { fmtDate, futureOrPast, DECISION, plural } from '../../ui.js';

export const CandidateOverview = {
  setup() {
    const inv = ref([]); const apps = ref([]); const tasks = ref([]);
    const loading = ref(true); const error = ref('');
    onMounted(async () => {
      try {
        const [i, a, t] = await Promise.all([api.get('/candidates/me/invitations'), api.get('/candidates/me/applications'), api.get('/candidates/me/short-tasks'), refreshMe()]);
        inv.value = i; apps.value = a; tasks.value = t;
      } catch (e) { error.value = e.detail; } finally { loading.value = false; }
    });
    const me = computed(() => store.me || {});
    const counts = computed(() => ({
      new: inv.value.filter((x) => x.status === 'sent').length,
      viewed: inv.value.filter((x) => x.status === 'viewed').length,
      accepted: inv.value.filter((x) => x.status === 'accepted').length,
      total: inv.value.length,
      apps: apps.value.length,
      tasksOpen: tasks.value.filter((t) => !t.answered).length,
    }));
    const steps = computed(() => {
      const m = me.value;
      return [
        { done: !!(m.full_name && m.city), text: 'Заполнить профиль: имя, город, стаж, стек', to: '/candidate/profile' },
        { done: !!(m.consents && m.consents.processing && m.consents.publication), text: 'Дать согласие на обработку данных и показ профиля работодателям', to: '/candidate/settings' },
        { done: !!m.grade, text: 'Пройти опрос и тест — получить категорию', to: '/candidate/test' },
        { done: !!m.fsp_id, text: 'Связать профиль с ФСП ID, чтобы подтвердить достижения (по желанию)', to: '/candidate/achievements' },
        { done: counts.value.new === 0, text: counts.value.new ? `Ответить на ${counts.value.new} ${plural(counts.value.new, 'новое приглашение', 'новых приглашения', 'новых приглашений')}` : 'Отвечать на приглашения работодателей', to: '/candidate/invitations' },
      ];
    });
    const changeLocked = computed(() => futureOrPast(me.value.grade_change_available_at));
    return { me, counts, steps, loading, error, fmtDate, categoryTitle, gradeTitle, specName, DECISION, changeLocked, store };
  },
  template: `
    <PageHead title="Обзор" :sub="me.alias ? 'Для работодателей вы — ' + me.alias + ', пока не примете приглашение.' : ''" />
    <div v-if="me.consents && !me.consents.publication" class="note note-warn">
      Работодатели вас <strong>не видят</strong>: нет согласия на показ профиля. Включить можно в <a href="#/candidate/settings">настройках</a>.
    </div>
    <div class="grid grid-4">
      <div class="stat accent">
        <div class="stat-label">Категория</div>
        <div class="stat-value" style="font-size:19px">{{ me.grade ? categoryTitle(me.specialization_code, me.grade) : 'не присвоена' }}</div>
        <div class="stat-sub" v-if="me.grade">грейд {{ gradeTitle(me.grade) }} · смена грейда {{ changeLocked ? 'с ' + fmtDate(me.grade_change_available_at) : 'доступна' }}</div>
        <div class="stat-sub" v-else>присваивается по результату теста</div>
      </div>
      <a class="stat" href="#/candidate/test">
        <div class="stat-label">Тестирование</div>
        <div class="stat-value" style="font-size:19px">{{ me.last_test ? (me.last_test.status === 'active' ? 'тест не завершён' : gradeTitle(me.last_test.result_grade)) : 'не пройдено' }}</div>
        <div class="stat-sub">{{ me.last_test ? (me.last_test.status === 'active' ? 'продолжить →' : (DECISION[me.last_test.decision] || '') + ' · ' + fmtDate(me.last_test.finished_at)) : 'опрос → грейд → тест, около 10 минут' }}</div>
      </a>
      <a class="stat" href="#/candidate/invitations">
        <div class="stat-label">Приглашения</div>
        <div class="stat-value">{{ counts.total }}</div>
        <div class="stat-sub">новых {{ counts.new }} · просмотрено {{ counts.viewed }} · принято {{ counts.accepted }}</div>
      </a>
      <a class="stat" href="#/candidate/applications">
        <div class="stat-label">Мои отклики и задания</div>
        <div class="stat-value">{{ counts.apps }}</div>
        <div class="stat-sub">откликов на вакансии · заданий без ответа: {{ counts.tasksOpen }}</div>
      </a>
    </div>
    <div class="grid grid-2" style="margin-top:14px">
      <div class="card">
        <h2>Что дальше</h2>
        <ul class="todo">
          <li v-for="s in steps" :key="s.text" :class="{ done: s.done }"><span class="mark">{{ s.done ? '✓' : '' }}</span><span class="text"><a v-if="!s.done" :href="'#' + s.to">{{ s.text }}</a><template v-else>{{ s.text }}</template></span></li>
        </ul>
      </div>
      <div class="card">
        <h2>Как это работает</h2>
        <p>Категорию «специализация × грейд» присваивает <strong>тест</strong>, а не самоописание. Работодатель видит вас по категории и подтверждённому стеку, без имени и контактов.</p>
        <p>Когда работодатель направит приглашение, вы увидите <strong>зарплату, компанию и предложение до начала общения</strong>. Контакты откроются только если вы примете приглашение.</p>
        <p class="muted" style="margin:0">Грейд не понижается принудительно: не прошли — можно попробовать уровень ниже; прошли уверенно — повысить. Смена не чаще раза в 90 дней.</p>
      </div>
    </div>`,
};
