/* Карточка кандидата для работодателя и окно приглашения. */
import { ref, reactive, computed, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, toast, skillName, formatTitle, CONTACT_METHODS } from '../../store.js';
import { moneyRange } from '../../ui.js';

export const InviteModal = {
  props: { card: Object, versionId: [Number, String] },
  emits: ['close', 'sent'],
  setup(props, { emit }) {
    const form = reactive({ message: '', salary: { min: props.card.salary_min ?? null, max: props.card.salary_max ?? null }, contact_method: 'Telegram', vacancy_id: '' });
    const vacancies = ref([]); const busy = ref(false); const error = ref('');
    onMounted(async () => { try { vacancies.value = await api.get('/employers/me/vacancies'); } catch (_) { /* список вакансий необязателен */ } });
    function pickVacancy() {
      const v = vacancies.value.find((x) => String(x.id) === String(form.vacancy_id));
      if (v) { form.salary = { min: v.salary_min, max: v.salary_max }; if (!form.message) form.message = `Приглашаем вас на вакансию «${v.title}».`; }
    }
    async function send() {
      error.value = '';
      if (!form.message.trim()) { error.value = 'Опишите предложение'; return; }
      if (form.salary.min === null || form.salary.max === null) { error.value = 'Зарплата «от» и «до» обязательна — кандидат видит условия до начала общения'; return; }
      if (form.salary.min > form.salary.max) { error.value = 'Зарплата «от» больше, чем «до»'; return; }
      busy.value = true;
      try {
        const body = { candidate_id: props.card.candidate_id, message: form.message.trim(), salary_min: form.salary.min, salary_max: form.salary.max, contact_method: form.contact_method };
        if (form.vacancy_id) body.vacancy_id = Number(form.vacancy_id);
        if (props.versionId) body.selection_version_id = props.versionId;
        await api.post('/invitations', body);
        toast(`Приглашение отправлено: ${props.card.alias}`, 'ok'); emit('sent'); emit('close');
      } catch (e) { error.value = e.detail; } finally { busy.value = false; }
    }
    return { form, vacancies, busy, error, send, pickVacancy, CONTACT_METHODS, moneyRange };
  },
  template: `
    <Modal :title="'Приглашение: ' + card.alias" @close="$emit('close')">
      <p class="muted" style="font-size:13.5px">Кандидат увидит компанию, описание предложения, зарплату и способ связи — до начала общения. Его контакты откроются вам после того, как он примет приглашение.</p>
      <form @submit.prevent="send" id="invite-form">
        <Field label="Вакансия (по желанию)" hint="Приглашение можно отправить и без вакансии">
          <select v-model="form.vacancy_id" @change="pickVacancy"><option value="">без привязки к вакансии</option><option v-for="v in vacancies" :key="v.id" :value="v.id">{{ v.title }} — {{ moneyRange(v.salary_min, v.salary_max) }}</option></select>
        </Field>
        <Field label="Описание предложения" required><textarea v-model="form.message" rows="4" required placeholder="Кем предстоит работать, над чем, почему выбрали этого кандидата"></textarea></Field>
        <MoneyRange v-model="form.salary" required label="Зарплата в месяц, ₽ (обязательно)" />
        <Field label="Способ связи" required><select v-model="form.contact_method" required><option v-for="m in CONTACT_METHODS" :key="m" :value="m">{{ m }}</option></select></Field>
        <div v-if="error" class="note note-err">{{ error }}</div>
      </form>
      <template #footer><button type="button" class="btn btn-ghost" @click="$emit('close')">Отмена</button><button form="invite-form" class="btn btn-primary" :disabled="busy"><span v-if="busy" class="spinner"></span>Отправить приглашение</button></template>
    </Modal>`,
};

export const CandidateCard = {
  components: { InviteModal },
  props: { card: Object, weights: Object, versionId: [Number, String], compact: Boolean, noInvite: Boolean, noScore: Boolean, scoreLabel: { type: String, default: 'соответствие потребности, из 100' } },
  emits: ['invited'],
  setup(props, { emit }) {
    const inviting = ref(false);
    const score100 = computed(() => Math.round((props.card.score || 0) * 100));
    const skills = computed(() => [...(props.card.skills || [])].sort((a, b) => Number(b.confirmed_by_test) - Number(a.confirmed_by_test)));
    const confirmedCount = computed(() => skills.value.filter((s) => s.confirmed_by_test).length);
    return { inviting, score100, skills, confirmedCount, skillName, formatTitle, moneyRange, onSent: () => emit('invited') };
  },
  template: `
    <div class="cand-card">
      <div>
        <div class="row-between" style="align-items:flex-start">
          <div>
            <div class="item-title" style="font-size:17px">{{ card.alias }}</div>
            <div class="item-meta">
              <span v-if="card.category" style="color:var(--violet);font-weight:500">{{ card.category.title }}</span>
              <span v-if="card.city">{{ card.city }}</span>
              <span v-if="card.work_format">{{ formatTitle(card.work_format) }}</span>
              <span v-if="card.salary_min || card.salary_max">ожидания {{ moneyRange(card.salary_min, card.salary_max) }}</span>
            </div>
          </div>
          <span v-if="card.fsp_linked" class="badge trust-source" title="Профиль связан с ФСП ID">ФСП ID</span>
        </div>
        <div v-if="card.explanation" class="explain">{{ card.explanation }}</div>
        <div class="chips" style="margin-bottom:8px">
          <Tag v-for="s in skills" :key="s.skill" :confirmed="s.confirmed_by_test">{{ s.name || skillName(s.skill) }}</Tag>
        </div>
        <div class="muted" style="font-size:12.5px;margin-bottom:8px" v-if="skills.length">Все навыки кандидата — подтверждено тестом: {{ confirmedCount }} из {{ skills.length }}</div>
        <div class="ach" v-if="card.achievements_summary">Достижения ФСП: <strong>{{ card.achievements_summary }}</strong></div>
        <div v-if="card.contacts_unlocked && card.contacts" class="contacts" style="margin-top:10px">
          <strong>Контакты открыты</strong>
          <dl class="kv" style="margin-top:4px"><dt>ФИО</dt><dd>{{ card.contacts.full_name || '—' }}</dd><dt>Телефон</dt><dd>{{ card.contacts.phone || '—' }}</dd><dt>Telegram</dt><dd>{{ card.contacts.telegram || '—' }}</dd><dt>Почта</dt><dd>{{ card.contacts.email || '—' }}</dd></dl>
        </div>
      </div>
      <div>
        <div class="score" v-if="!noScore && card.score !== undefined && card.score !== null" :title="card.raw_score !== undefined ? 'Калиброванная оценка: ' + score100 + ' означает, что по нашим данным подходят примерно ' + Math.round(score100 / 10) + ' из 10 кандидатов с таким профилем. Сырой итог формулы: ' + Math.round(card.raw_score * 100) : ''">
          <div class="score-val">{{ score100 }}</div>
          <div class="score-lbl">{{ scoreLabel }}</div>
        </div>
        <ScoreParts v-if="!noScore && card.parts" :parts="card.parts" :weights="weights" compact style="margin:10px 0" />
        <button v-if="!noInvite" type="button" class="btn btn-primary btn-block" @click="inviting = true">Пригласить</button>
      </div>
      <InviteModal v-if="inviting" :card="card" :version-id="versionId" @close="inviting = false" @sent="onSent" />
    </div>`,
};
