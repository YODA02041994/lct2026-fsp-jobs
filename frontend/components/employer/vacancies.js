/* Вакансии работодателя: список, форма, отклики, предпросмотр теста под вакансию. */
import { ref, reactive, computed, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, toast, confirmDialog, specName, gradeTitle, formatTitle, skillName, skillCode } from '../../store.js';
import { route, navigate } from '../../router.js';
import { useLoad, moneyRange, fmtDate, fmtDateTime } from '../../ui.js';
import { CandidateCard } from './candidate-card.js';

export const EmployerVacancies = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/employers/me/vacancies'));
    const preview = ref(null); const previewFor = ref(null); const previewBusy = ref(false);
    async function showPreview(v) {
      previewFor.value = v; previewBusy.value = true; preview.value = null;
      try { preview.value = await api.get(`/vacancies/${v.id}/test-preview`); } catch (e) { toast(e.detail, 'err'); previewFor.value = null; } finally { previewBusy.value = false; }
    }
    return { data, loading, error, reload, preview, previewFor, previewBusy, showPreview, specName, gradeTitle, formatTitle, skillName, moneyRange, fmtDate };
  },
  template: `
    <PageHead title="Вакансии" sub="Дополнительный путь: кандидат откликается сам, и вы сразу видите его контакты. Зарплата «от – до» обязательна.">
      <a href="#/employer/vacancies/new" class="btn btn-primary">Создать вакансию</a>
    </PageHead>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Вакансий пока нет" empty-hint="Создайте вакансию — она появится в списке у кандидатов. По описанию система покажет, как будут выглядеть задания теста под неё." @retry="reload">
      <template #empty><a href="#/employer/vacancies/new" class="btn btn-primary">Создать вакансию</a></template>
      <div class="list">
        <div v-for="v in data" :key="v.id" class="item">
          <div class="row-between">
            <div>
              <div class="item-title">{{ v.title }} <StatusBadge v-if="v.status" :status="v.status" style="margin-left:6px" /></div>
              <div class="item-meta"><span>{{ specName(v.specialization_code) }} · {{ gradeTitle(v.grade) }}</span><span>{{ formatTitle(v.work_format) }}<template v-if="v.city">, {{ v.city }}</template></span><span>{{ fmtDate(v.created_at) }}</span></div>
            </div>
            <div class="price big">{{ moneyRange(v.salary_min, v.salary_max) }}</div>
          </div>
          <div class="chips" style="margin:8px 0"><span v-for="s in v.stack" :key="s" class="chip">{{ skillName(s) }}</span></div>
          <div class="row">
            <a :href="'#/employer/vacancies/' + v.id + '/applications'" class="btn btn-secondary btn-sm">Отклики<template v-if="v.applications_count !== undefined"> ({{ v.applications_count }})</template></a>
            <a :href="'#/employer/vacancies/' + v.id + '/edit'" class="btn btn-outline btn-sm">Редактировать</a>
            <button type="button" class="btn btn-ghost btn-sm" @click="showPreview(v)">Как будет выглядеть тест под эту вакансию</button>
          </div>
        </div>
      </div>
    </Loader>
    <Modal v-if="previewFor" :title="'Задания под вакансию «' + previewFor.title + '»'" wide @close="previewFor = null">
      <p class="muted" style="font-size:13.5px">Из описания извлечены технологии, под них подобраны шаблоны заданий из банка. Каждому кандидату достанется свой экземпляр с теми же сложностью и проверяемым умением — поэтому результаты сопоставимы, а задания не расходятся.</p>
      <div v-if="previewBusy" class="state"><span class="spinner"></span> Собираем задания…</div>
      <template v-else-if="preview">
        <div class="chips" style="margin-bottom:12px"><span class="muted" style="font-size:13px">Технологии:</span><span v-for="t in preview.technologies" :key="t" class="chip chip-tech">{{ skillName(t) }}</span></div>
        <div class="stack"><div v-for="(it, i) in preview.items" :key="i" class="card" style="padding:14px"><div class="muted" style="font-size:12.5px;margin-bottom:6px">Задание {{ i + 1 }}</div><TestItemView :payload="it" readonly /></div></div>
      </template>
    </Modal>`,
};

export const EmployerVacancyForm = {
  setup() {
    const id = route.params.id;
    const form = reactive({ title: '', description: '', specialization_code: '', grade: '', stack: [], salary: { min: null, max: null }, work_format: '', city: '' });
    const busy = ref(false); const error = ref(''); const loading = ref(!!id);
    const skillNames = computed(() => store.catalog.skills.map((s) => s.name));
    onMounted(async () => {
      if (!id) return;
      try {
        const v = await api.get(`/vacancies/${id}`);
        Object.assign(form, { title: v.title, description: v.description || '', specialization_code: v.specialization_code || '', grade: v.grade || '', stack: (v.stack || []).map(skillName), salary: { min: v.salary_min, max: v.salary_max }, work_format: v.work_format || '', city: v.city || '' });
      } catch (e) { error.value = e.detail; } finally { loading.value = false; }
    });
    async function save() {
      error.value = '';
      if (form.salary.min === null || form.salary.max === null) { error.value = 'Зарплата «от» и «до» обязательна'; return; }
      if (form.salary.min > form.salary.max) { error.value = 'Зарплата «от» больше, чем «до»'; return; }
      busy.value = true;
      try {
        const body = { title: form.title.trim(), description: form.description.trim(), specialization_code: form.specialization_code || null, grade: form.grade || null, stack: form.stack.map(skillCode), salary_min: form.salary.min, salary_max: form.salary.max, work_format: form.work_format || null, city: form.city.trim() };
        if (id) await api.put(`/vacancies/${id}`, body); else await api.post('/vacancies', body);
        toast(id ? 'Вакансия сохранена' : 'Вакансия опубликована', 'ok'); navigate('/employer/vacancies');
      } catch (e) { error.value = e.detail; } finally { busy.value = false; }
    }
    return { id, form, busy, error, loading, save, skillNames, store };
  },
  template: `
    <PageHead :title="id ? 'Редактировать вакансию' : 'Новая вакансия'" sub="Описание увидят кандидаты. По нему же система соберёт задания теста под вакансию.">
      <a href="#/employer/vacancies" class="btn btn-ghost">К списку</a>
    </PageHead>
    <div v-if="loading" class="state"><span class="spinner"></span> Загрузка…</div>
    <form v-else class="card" style="max-width:860px" @submit.prevent="save">
      <Field label="Название" required><input v-model="form.title" type="text" required></Field>
      <Field label="Описание" required hint="Задачи, команда, стек, условия"><textarea v-model="form.description" rows="6" required></textarea></Field>
      <div class="form-grid">
        <Field label="Специализация"><select v-model="form.specialization_code"><option value="">не указана</option><option v-for="s in store.catalog.specializations" :key="s.code" :value="s.code">{{ s.name }}</option></select></Field>
        <Field label="Грейд"><select v-model="form.grade"><option value="">не указан</option><option v-for="g in store.catalog.grades" :key="g.code" :value="g.code">{{ g.title }}</option></select></Field>
        <div class="span-2"><Field label="Стек" hint="Если оставить пустым — технологии извлекутся из описания"><TagsInput v-model="form.stack" :suggestions="skillNames" placeholder="технология" /></Field></div>
        <div class="span-2"><MoneyRange v-model="form.salary" required label="Зарплата в месяц, ₽ (обязательно)" /></div>
        <Field label="Формат работы"><select v-model="form.work_format"><option value="">не указан</option><option v-for="f in store.catalog.work_formats" :key="f.code" :value="f.code">{{ f.title }}</option></select></Field>
        <Field label="Город"><input v-model="form.city" type="text"></Field>
      </div>
      <div v-if="error" class="note note-err">{{ error }}</div>
      <div class="form-actions"><button class="btn btn-primary" :disabled="busy"><span v-if="busy" class="spinner"></span>{{ id ? 'Сохранить' : 'Опубликовать' }}</button></div>
    </form>`,
};

export const EmployerVacancyApplications = {
  components: { CandidateCard },
  setup() {
    const id = route.params.id;
    const vacancy = ref(null);
    const { data, loading, error, reload } = useLoad(async () => { try { vacancy.value = await api.get(`/vacancies/${id}`); } catch (_) { /* заголовок необязателен */ } return api.get(`/vacancies/${id}/applications`); });
    const busy = ref(null);
    async function setStatus(a, status) {
      if (status === 'declined') { const ok = await confirmDialog({ title: 'Отклонить отклик?', text: 'Кандидат увидит статус «отклонено».', ok: 'Отклонить', danger: true }); if (!ok) return; }
      busy.value = a.id;
      try { await api.patch(`/applications/${a.id}`, { status }); a.status = status; toast('Статус обновлён', 'ok'); } catch (e) { toast(e.detail, 'err'); } finally { busy.value = null; }
    }
    return { id, vacancy, data, loading, error, reload, setStatus, busy, moneyRange, fmtDateTime };
  },
  template: `
    <PageHead :title="'Отклики: ' + (vacancy ? vacancy.title : 'вакансия № ' + id)" :sub="vacancy ? moneyRange(vacancy.salary_min, vacancy.salary_max) : ''">
      <a href="#/employer/vacancies" class="btn btn-ghost">К вакансиям</a>
    </PageHead>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Откликов пока нет" empty-hint="Когда кандидат откликнется, здесь появятся его карточка, сообщение и контакты." @retry="reload">
      <div class="list">
        <div v-for="a in data" :key="a.id" class="card">
          <div class="row-between" style="margin-bottom:10px">
            <div class="row"><StatusBadge :status="a.status" /><span class="muted" style="font-size:13px">отклик {{ fmtDateTime(a.created_at) }}</span></div>
            <div class="row">
              <button v-if="a.status === 'sent'" type="button" class="btn btn-ghost btn-sm" :disabled="busy === a.id" @click="setStatus(a, 'viewed')">Отметить просмотренным</button>
              <button v-if="a.status !== 'accepted' && a.status !== 'declined'" type="button" class="btn btn-primary btn-sm" :disabled="busy === a.id" @click="setStatus(a, 'accepted')">Принять</button>
              <button v-if="a.status !== 'accepted' && a.status !== 'declined'" type="button" class="btn btn-danger btn-sm" :disabled="busy === a.id" @click="setStatus(a, 'declined')">Отклонить</button>
            </div>
          </div>
          <div v-if="a.message" class="note note-info"><strong>Сообщение кандидата:</strong> <span class="pre-wrap">{{ a.message }}</span></div>
          <CandidateCard :card="a.candidate" no-invite no-score />
        </div>
      </div>
    </Loader>`,
};
