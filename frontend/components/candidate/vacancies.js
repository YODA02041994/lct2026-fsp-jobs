/* Вакансии: список с фильтрами, карточка, отклик, мои отклики. */
import { ref, reactive, computed, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, toast, specName, gradeTitle, formatTitle, skillName } from '../../store.js';
import { route, navigate } from '../../router.js';
import { useLoad, moneyRange, fmtDate, fmtDateTime } from '../../ui.js';

export const CandidateVacancies = {
  setup() {
    const f = reactive({ specialization: '', grade: '', skill: '', q: '' });
    const { data, loading, error, reload } = useLoad(() => api.get('/vacancies', { specialization: f.specialization, grade: f.grade, skill: f.skill, q: f.q }));
    let t = null;
    function changed() { clearTimeout(t); t = setTimeout(reload, 250); }
    function clear() { Object.assign(f, { specialization: '', grade: '', skill: '', q: '' }); reload(); }
    return { f, data, loading, error, reload, changed, clear, store, specName, gradeTitle, formatTitle, skillName, moneyRange, fmtDate };
  },
  template: `
    <PageHead title="Вакансии" sub="Открытые вакансии работодателей платформы. Зарплата указана всегда — это правило платформы. Можно откликнуться самому: тогда работодатель увидит ваши контакты.">
      <a href="#/candidate/applications" class="btn btn-outline">Мои отклики</a>
    </PageHead>
    <div class="card" style="margin-bottom:14px">
      <div class="form-grid" style="grid-template-columns: 2fr 1fr 1fr 1fr">
        <Field label="Поиск"><input v-model="f.q" type="search" placeholder="название, компания, слово из описания" @input="changed"></Field>
        <Field label="Специализация"><select v-model="f.specialization" @change="reload"><option value="">любая</option><option v-for="s in store.catalog.specializations" :key="s.code" :value="s.code">{{ s.name }}</option></select></Field>
        <Field label="Грейд"><select v-model="f.grade" @change="reload"><option value="">любой</option><option v-for="g in store.catalog.grades" :key="g.code" :value="g.code">{{ g.title }}</option></select></Field>
        <Field label="Технология"><select v-model="f.skill" @change="reload"><option value="">любая</option><option v-for="s in store.catalog.skills" :key="s.code" :value="s.code">{{ s.name }}</option></select></Field>
      </div>
      <button type="button" class="btn btn-ghost btn-sm" @click="clear">Сбросить фильтры</button>
    </div>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Вакансий по этим условиям нет" empty-hint="Попробуйте снять часть фильтров. Основной путь на платформе — приглашения от работодателей, вакансии дополняют его." @retry="reload">
      <div class="list">
        <a v-for="v in data" :key="v.id" class="item" :href="'#/candidate/vacancies/' + v.id">
          <div class="row-between">
            <div>
              <div class="item-title">{{ v.title }}</div>
              <div class="item-meta"><span>{{ v.company_name }}</span><span>{{ specName(v.specialization_code) }} · {{ gradeTitle(v.grade) }}</span><span>{{ formatTitle(v.work_format) }}<template v-if="v.city">, {{ v.city }}</template></span><span>{{ fmtDate(v.created_at) }}</span></div>
            </div>
            <div class="price big">{{ moneyRange(v.salary_min, v.salary_max) }}</div>
          </div>
          <div class="chips" style="margin-top:8px"><span v-for="s in v.stack" :key="s" class="chip">{{ skillName(s) }}</span></div>
        </a>
      </div>
    </Loader>`,
};

export const CandidateVacancyPage = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get(`/vacancies/${route.params.id}`));
    const apps = useLoad(() => api.get('/candidates/me/applications'));
    const modal = ref(false); const message = ref(''); const busy = ref(false);
    const mine = computed(() => (apps.data.value || []).find((a) => a.vacancy && String(a.vacancy.id) === String(route.params.id)));
    const mySkills = computed(() => new Set((store.me && store.me.skills || []).map((s) => s.skill)));
    async function apply() {
      busy.value = true;
      try { await api.post(`/vacancies/${route.params.id}/apply`, { message: message.value.trim() }); modal.value = false; toast('Отклик отправлен. Работодатель увидит ваши контакты', 'ok'); apps.reload(); }
      catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    return { data, loading, error, reload, modal, message, busy, apply, mine, mySkills, specName, gradeTitle, formatTitle, skillName, moneyRange, fmtDate, fmtDateTime };
  },
  template: `
    <Loader :loading="loading" :error="error" @retry="reload">
      <template v-if="data">
        <PageHead :title="data.title" :sub="data.company_name">
          <a href="#/candidate/vacancies" class="btn btn-ghost">К списку</a>
        </PageHead>
        <div class="grid" style="grid-template-columns: 1fr 320px; align-items:start">
          <div class="card">
            <div class="chips" style="margin-bottom:12px"><span class="chip">{{ specName(data.specialization_code) }}</span><span class="chip">{{ gradeTitle(data.grade) }}</span><span class="chip chip-muted">{{ formatTitle(data.work_format) }}<template v-if="data.city">, {{ data.city }}</template></span></div>
            <h3>Описание</h3>
            <p class="pre-wrap">{{ data.description }}</p>
            <h3>Стек</h3>
            <div class="chips"><Tag v-for="s in data.stack" :key="s" :confirmed="mySkills.has(s)">{{ skillName(s) }}</Tag></div>
            <p class="muted" style="font-size:12.5px;margin-top:8px">Отмечены технологии, которые есть в вашем профиле.</p>
          </div>
          <div class="card">
            <div class="muted" style="font-size:13px">Зарплата в месяц</div>
            <div class="price big" style="font-size:24px">{{ moneyRange(data.salary_min, data.salary_max) }}</div>
            <div class="muted" style="font-size:13px;margin-bottom:12px">опубликована {{ fmtDate(data.created_at) }}</div>
            <div v-if="mine" class="note note-ok">Вы откликнулись {{ fmtDateTime(mine.created_at) }}. Статус: <StatusBadge :status="mine.status" /></div>
            <button v-else type="button" class="btn btn-primary btn-block" @click="modal = true">Откликнуться</button>
            <p class="muted" style="font-size:12.5px;margin-top:10px">Откликаясь, вы открываете работодателю ФИО и контакты — как при принятии приглашения.</p>
          </div>
        </div>
      </template>
    </Loader>
    <Modal v-if="modal" title="Отклик на вакансию" @close="modal = false">
      <Field label="Сопроводительное сообщение" hint="Кратко: почему вам интересна эта вакансия"><textarea v-model="message" rows="5"></textarea></Field>
      <div class="note note-info">После отклика работодатель увидит ваши ФИО, телефон, Telegram и почту.</div>
      <template #footer><button type="button" class="btn btn-ghost" @click="modal = false">Отмена</button><button type="button" class="btn btn-primary" :disabled="busy" @click="apply"><span v-if="busy" class="spinner"></span>Отправить отклик</button></template>
    </Modal>`,
};

export const CandidateApplications = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/candidates/me/applications'));
    return { data, loading, error, reload, moneyRange, fmtDateTime };
  },
  template: `
    <PageHead title="Мои отклики" sub="Отклики видите только вы и работодатель, которому они направлены.">
      <a href="#/candidate/vacancies" class="btn btn-outline">К вакансиям</a>
    </PageHead>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Откликов пока нет" empty-hint="Найдите вакансию в списке и нажмите «Откликнуться»." @retry="reload">
      <template #empty><a href="#/candidate/vacancies" class="btn btn-primary">Смотреть вакансии</a></template>
      <div class="list">
        <a v-for="a in data" :key="a.id" class="item" :href="'#/candidate/vacancies/' + a.vacancy.id">
          <div class="row-between">
            <div><div class="item-title">{{ a.vacancy.title }} <StatusBadge :status="a.status" style="margin-left:6px" /></div><div class="item-meta"><span>{{ a.vacancy.company_name }}</span><span>отклик {{ fmtDateTime(a.created_at) }}</span></div></div>
            <div class="price">{{ moneyRange(a.vacancy.salary_min, a.vacancy.salary_max) }}</div>
          </div>
        </a>
      </div>
    </Loader>`,
};
