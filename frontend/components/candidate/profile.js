/* Профиль кандидата: форма, резюме из PDF, PDF-профиль. */
import { reactive, ref, computed, onMounted } from 'vue';
import { api, downloadFile } from '../../api.js';
import { store, refreshMe, toast, categoryTitle, gradeTitle } from '../../store.js';
import { fmtDate } from '../../ui.js';

function fromMe(m) {
  return {
    full_name: m.full_name || '', phone: m.phone || '', telegram: m.telegram || '', city: m.city || '',
    experience_years: m.experience_years ?? '', roles: [...(m.roles || [])], soft_skills: [...(m.soft_skills || [])], about: m.about || '',
    salary: { min: m.salary_min ?? null, max: m.salary_max ?? null }, work_format: m.work_format || '',
    skills: (m.skills || []).map((s) => s.name || s.skill),
  };
}

export const CandidateProfile = {
  setup() {
    const me = computed(() => store.me || {});
    const form = reactive(fromMe(store.me || {}));
    const busy = ref(false); const error = ref('');
    const parsed = ref(null); const uploading = ref(false); const fileInput = ref(null);
    const skillNames = computed(() => (store.catalog ? store.catalog.skills.map((s) => s.name) : []));
    const confirmedSet = computed(() => new Set((me.value.skills || []).filter((s) => s.confirmed_by_test).map((s) => s.name)));
    onMounted(async () => { await refreshMe(); Object.assign(form, fromMe(store.me || {})); });

    function payload() {
      return {
        full_name: form.full_name.trim(), phone: form.phone.trim(), telegram: form.telegram.trim(), city: form.city.trim(),
        experience_years: form.experience_years === '' ? null : Number(form.experience_years), roles: form.roles, soft_skills: form.soft_skills,
        about: form.about.trim(), salary_min: form.salary.min, salary_max: form.salary.max, work_format: form.work_format || null, skills: form.skills,
      };
    }
    async function save() {
      error.value = '';
      if (form.salary.min !== null && form.salary.max !== null && form.salary.min > form.salary.max) { error.value = 'Зарплата «от» больше, чем «до»'; return; }
      busy.value = true;
      try { store.me = await api.put('/candidates/me', payload()); Object.assign(form, fromMe(store.me)); toast('Профиль сохранён', 'ok'); }
      catch (e) { error.value = e.detail; } finally { busy.value = false; }
    }
    async function upload(ev) {
      const file = ev.target.files && ev.target.files[0];
      if (!file) return;
      if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') { toast('Нужен файл PDF', 'warn'); ev.target.value = ''; return; }
      uploading.value = true; parsed.value = null;
      try {
        const fd = new FormData(); fd.append('file', file);
        const r = await api.upload('/candidates/me/resume', fd);
        parsed.value = r.parsed;
        await refreshMe(); Object.assign(form, fromMe(store.me));
        toast(r.applied ? 'Резюме распознано: пустые поля заполнены. Проверьте и сохраните' : 'Резюме распознано. Выберите, что подставить', 'ok');
      } catch (e) { toast(e.detail, 'err'); } finally { uploading.value = false; ev.target.value = ''; }
    }
    function applyParsed() {
      const p = parsed.value; if (!p) return;
      const map = { full_name: 'full_name', phone: 'phone', telegram: 'telegram', city: 'city', about: 'about' };
      Object.entries(map).forEach(([k, f]) => { if (p[k]) form[f] = p[k]; });
      if (p.experience_years !== undefined && p.experience_years !== null) form.experience_years = p.experience_years;
      if (p.roles && p.roles.length) form.roles = [...p.roles];
      if (p.soft_skills && p.soft_skills.length) form.soft_skills = [...p.soft_skills];
      if (p.skills && p.skills.length) form.skills = Array.from(new Set([...form.skills, ...p.skills]));
      toast('Поля заполнены из резюме. Нажмите «Сохранить»', 'ok');
    }
    async function pdf() {
      try { await downloadFile('/candidates/me/profile.pdf', 'profile-fsp.pdf'); } catch (e) { toast(e.detail, 'err'); }
    }
    return { me, form, busy, error, save, upload, uploading, parsed, applyParsed, pdf, fileInput, skillNames, confirmedSet, store, categoryTitle, gradeTitle, fmtDate };
  },
  template: `
    <PageHead title="Профиль" sub="Работодатели видят профиль без имени и контактов — как «Кандидат № …» с категорией, стеком и достижениями. Контакты откроются после того, как вы примете приглашение.">
      <button type="button" class="btn btn-outline" @click="pdf">Скачать PDF-профиль</button>
    </PageHead>
    <div class="grid" style="grid-template-columns: 1fr 320px; align-items:start">
      <div>
        <form class="card" @submit.prevent="save">
          <h2>Основное</h2>
          <div class="form-grid">
            <Field label="Фамилия, имя, отчество" required><input v-model="form.full_name" type="text" required autocomplete="name"></Field>
            <Field label="Город"><input v-model="form.city" type="text" autocomplete="address-level2"></Field>
            <Field label="Телефон"><input v-model="form.phone" type="tel" placeholder="+7 ..."></Field>
            <Field label="Telegram"><input v-model="form.telegram" type="text" placeholder="@имя"></Field>
            <Field label="Стаж в ИТ, лет"><input v-model="form.experience_years" type="number" min="0" max="60" step="1"></Field>
            <Field label="Формат работы">
              <select v-model="form.work_format"><option value="">не важно</option><option v-for="f in store.catalog.work_formats" :key="f.code" :value="f.code">{{ f.title }}</option></select>
            </Field>
            <div class="span-2"><MoneyRange v-model="form.salary" label="Ожидания по зарплате в месяц, ₽" /></div>
            <div class="span-2"><Field label="Роли" hint="Например: бэкенд-разработчик, тимлид. Enter или запятая — добавить"><TagsInput v-model="form.roles" placeholder="роль" /></Field></div>
            <div class="span-2"><Field label="Гибкие навыки" hint="Коммуникация, наставничество, работа в команде…"><TagsInput v-model="form.soft_skills" placeholder="навык" /></Field></div>
            <div class="span-2"><Field label="О себе"><textarea v-model="form.about" rows="4" placeholder="Чем занимались, что умеете, что ищете"></textarea></Field></div>
            <div class="span-2">
              <Field label="Стек технологий" hint="Заявленные технологии учитываются при подборе частично; подтверждённые тестом — полностью">
                <TagsInput v-model="form.skills" :suggestions="skillNames" placeholder="технология">
                  <template #tag="{ value }"><span :class="{ 'tag-confirmed': confirmedSet.has(value) }" style="display:inline-flex;gap:4px">{{ value }}<span v-if="confirmedSet.has(value)" class="tag-check" title="подтверждено тестом">✓</span></span></template>
                </TagsInput>
              </Field>
            </div>
          </div>
          <div v-if="error" class="note note-err">{{ error }}</div>
          <div class="form-actions"><button class="btn btn-primary" :disabled="busy"><span v-if="busy" class="spinner"></span>Сохранить</button></div>
        </form>
      </div>
      <div class="stack">
        <div class="card">
          <h3>Категория</h3>
          <div style="font-weight:600;color:var(--violet)">{{ me.grade ? categoryTitle(me.specialization_code, me.grade) : 'не присвоена' }}</div>
          <p class="muted" style="font-size:13px;margin-top:4px">{{ me.grade ? 'Определена тестом. Заявленный грейд: ' + gradeTitle(me.claimed_grade) : 'Пройдите опрос и тест — категория появится здесь.' }}</p>
          <a href="#/candidate/test" class="btn btn-outline btn-sm">{{ me.grade ? 'Тестирование' : 'Пройти тест' }}</a>
        </div>
        <div class="card">
          <h3>Резюме из PDF</h3>
          <p class="muted" style="font-size:13px">Загрузите резюме — распознаем ФИО, контакты, стек, роли, стаж и гибкие навыки. Пустые поля заполнятся сами, заполненные не перезапишутся без вашего согласия.</p>
          <label class="btn btn-secondary btn-block" :class="{ disabled: uploading }">
            <span v-if="uploading" class="spinner"></span>{{ uploading ? 'Распознаём…' : 'Загрузить резюме (PDF)' }}
            <input type="file" accept="application/pdf,.pdf" style="display:none" @change="upload" :disabled="uploading">
          </label>
          <div v-if="parsed" class="note note-info" style="margin-top:12px;margin-bottom:0">
            <strong>Распознано:</strong>
            <dl class="kv" style="margin:8px 0;grid-template-columns:1fr">
              <dd v-if="parsed.full_name">{{ parsed.full_name }}</dd>
              <dd v-if="parsed.city || parsed.experience_years !== null">{{ parsed.city }}<template v-if="parsed.experience_years !== null && parsed.experience_years !== undefined"> · стаж {{ parsed.experience_years }} л.</template></dd>
              <dd v-if="parsed.skills && parsed.skills.length"><span class="chips"><span v-for="s in parsed.skills" :key="s" class="chip">{{ s }}</span></span></dd>
            </dl>
            <button type="button" class="btn btn-outline btn-sm" @click="applyParsed">Подставить всё в форму</button>
          </div>
        </div>
        <div class="card">
          <h3>ФСП ID</h3>
          <p v-if="me.fsp_id" style="font-size:14px;margin:0">Связан: <strong>{{ me.fsp_id }}</strong><br><span class="muted" style="font-size:13px">с {{ fmtDate(me.fsp_linked_at) }}</span></p>
          <p v-else class="muted" style="font-size:13px">Не связан. Связать можно в разделе <a href="#/candidate/achievements">«Достижения ФСП»</a>.</p>
        </div>
      </div>
    </div>`,
};
