/* Профиль компании. */
import { reactive, ref, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, refreshMe, toast } from '../../store.js';

const FIELDS = ['company_name', 'description', 'industry', 'website', 'city', 'contact_person', 'contact_email', 'contact_phone'];

export const EmployerCompany = {
  setup() {
    const form = reactive(Object.fromEntries(FIELDS.map((f) => [f, ''])));
    const busy = ref(false); const error = ref('');
    function fill() { FIELDS.forEach((f) => { form[f] = (store.me && store.me[f]) || ''; }); }
    onMounted(async () => { await refreshMe(); fill(); });
    async function save() {
      error.value = ''; busy.value = true;
      try { store.me = await api.put('/employers/me', { ...form }); fill(); toast('Профиль компании сохранён', 'ok'); }
      catch (e) { error.value = e.detail; } finally { busy.value = false; }
    }
    return { form, busy, error, save };
  },
  template: `
    <PageHead title="Профиль компании" sub="Название и описание кандидат видит в приглашении — вместе с зарплатой и способом связи." />
    <form class="card" @submit.prevent="save" style="max-width:860px">
      <div class="form-grid">
        <Field label="Название компании" required><input v-model="form.company_name" type="text" required></Field>
        <Field label="Направление деятельности"><input v-model="form.industry" type="text" placeholder="например: разработка ПО, финтех"></Field>
        <div class="span-2"><Field label="Описание" hint="Чем занимается компания и команда, что предстоит делать кандидатам"><textarea v-model="form.description" rows="4"></textarea></Field></div>
        <Field label="Сайт"><input v-model="form.website" type="url" placeholder="https://"></Field>
        <Field label="Город"><input v-model="form.city" type="text"></Field>
        <Field label="Контактное лицо"><input v-model="form.contact_person" type="text"></Field>
        <Field label="Почта для связи"><input v-model="form.contact_email" type="email"></Field>
        <Field label="Телефон"><input v-model="form.contact_phone" type="tel"></Field>
      </div>
      <div v-if="error" class="note note-err">{{ error }}</div>
      <div class="form-actions"><button class="btn btn-primary" :disabled="busy"><span v-if="busy" class="spinner"></span>Сохранить</button></div>
    </form>`,
};
