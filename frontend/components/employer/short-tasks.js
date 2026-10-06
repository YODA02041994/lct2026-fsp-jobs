/* Короткие задания работодателя: создание, ответы кандидатов, оценка 1–5. */
import { ref, reactive, computed } from 'vue';
import { api } from '../../api.js';
import { store, toast, specName, skillName, skillCode } from '../../store.js';
import { useLoad, fmtDate, fmtDateTime } from '../../ui.js';

export const EmployerShortTasks = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/employers/me/short-tasks'));
    const creating = ref(false); const busy = ref(false); const scoring = ref(null);
    const form = reactive({ title: '', text: '', specialization_code: '', technologies: [] });
    const skillNames = computed(() => store.catalog.skills.map((s) => s.name));
    async function create() {
      busy.value = true;
      try {
        const body = { title: form.title.trim(), text: form.text.trim() };
        if (form.specialization_code) body.specialization_code = form.specialization_code;
        if (form.technologies.length) body.technologies = form.technologies.map(skillCode);
        await api.post('/short-tasks', body);
        Object.assign(form, { title: '', text: '', specialization_code: '', technologies: [] }); creating.value = false; await reload(); toast('Задание опубликовано для кандидатов', 'ok');
      } catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    async function score(ans, value) {
      if (!ans.id) { toast('В ответе нет идентификатора — оценка недоступна', 'err'); return; }
      scoring.value = ans.id;
      try { await api.patch(`/short-task-answers/${ans.id}`, { employer_score: value }); ans.employer_score = value; toast(`Оценка ${value} из 5 сохранена`, 'ok'); }
      catch (e) { toast(e.detail, 'err'); } finally { scoring.value = null; }
    }
    return { data, loading, error, reload, creating, busy, form, create, score, scoring, skillNames, store, specName, skillName, fmtDate, fmtDateTime };
  },
  template: `
    <PageHead title="Короткие задания" sub="Небольшой практический вопрос для кандидатов выбранной специализации. Ответы оцениваете вы по шкале от 1 до 5; оценка повышает актуальность профиля кандидата, но на грейд не влияет.">
      <button type="button" class="btn btn-primary" @click="creating = true">Создать задание</button>
    </PageHead>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Заданий пока нет" empty-hint="Создайте задание — его увидят кандидаты выбранной специализации в своём кабинете." @retry="reload">
      <template #empty><button type="button" class="btn btn-primary" @click="creating = true">Создать задание</button></template>
      <div class="list">
        <div v-for="t in data" :key="t.id" class="card">
          <div class="row-between"><div><h3 style="margin-bottom:2px">{{ t.title }}</h3><div class="item-meta"><span>{{ t.specialization_code ? specName(t.specialization_code) : 'все специализации' }}</span><span v-if="t.created_at">{{ fmtDate(t.created_at) }}</span></div></div><span class="badge">ответов: {{ t.answers.length }}</span></div>
          <div class="chips" style="margin:8px 0"><span v-for="s in t.technologies" :key="s" class="chip chip-tech">{{ skillName(s) }}</span></div>
          <p class="pre-wrap muted" style="font-size:14px">{{ t.text }}</p>
          <div v-if="!t.answers.length" class="muted" style="font-size:13px">Ответов пока нет.</div>
          <div v-else class="stack">
            <div v-for="a in t.answers" :key="a.id || a.created_at" class="item" style="box-shadow:none">
              <div class="row-between"><strong style="color:var(--violet)">{{ a.candidate.alias }}</strong><span class="muted" style="font-size:13px">{{ fmtDateTime(a.created_at) }}</span></div>
              <p class="pre-wrap" style="margin:6px 0">{{ a.answer }}</p>
              <div class="row"><span class="muted" style="font-size:13px">Оценка:</span><div class="score-pick"><button v-for="n in 5" :key="n" type="button" :class="{ on: a.employer_score === n }" :disabled="scoring === a.id" @click="score(a, n)">{{ n }}</button></div><span v-if="a.employer_score" class="muted" style="font-size:13px">{{ a.employer_score }} из 5</span></div>
            </div>
          </div>
        </div>
      </div>
    </Loader>
    <Modal v-if="creating" title="Новое короткое задание" @close="creating = false">
      <form id="task-form" @submit.prevent="create">
        <Field label="Заголовок" required><input v-model="form.title" type="text" required></Field>
        <Field label="Текст задания" required hint="Ситуация из практики и вопрос «как поступите»"><textarea v-model="form.text" rows="5" required></textarea></Field>
        <Field label="Специализация" hint="Кому показывать; пусто — всем"><select v-model="form.specialization_code"><option value="">всем</option><option v-for="s in store.catalog.specializations" :key="s.code" :value="s.code">{{ s.name }}</option></select></Field>
        <Field label="Технологии" hint="Если пусто — извлекутся из текста"><TagsInput v-model="form.technologies" :suggestions="skillNames" placeholder="технология" /></Field>
      </form>
      <template #footer><button type="button" class="btn btn-ghost" @click="creating = false">Отмена</button><button form="task-form" class="btn btn-primary" :disabled="busy"><span v-if="busy" class="spinner"></span>Опубликовать</button></template>
    </Modal>`,
};
