/* Настройки: согласия и приватность. */
import { reactive, ref, computed, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, refreshMe, toast, confirmDialog } from '../../store.js';

export const CandidateSettings = {
  setup() {
    const me = computed(() => store.me || {});
    const consents = reactive({ processing: false, publication: false });
    const privacy = reactive({ achievements: true, city: true, salary: true, fsp_link: true, visible_to_employers: true });
    const busyC = ref(false); const busyP = ref(false);
    function fill() {
      const m = store.me || {};
      Object.assign(consents, m.consents || {});
      Object.assign(privacy, m.privacy || {}, { visible_to_employers: m.visible_to_employers !== false });
    }
    onMounted(async () => { await refreshMe(); fill(); });
    async function saveConsents() {
      if (!consents.processing) {
        const ok = await confirmDialog({ title: 'Отозвать согласие на обработку?', text: 'Без согласия на обработку персональных данных платформа не сможет хранить ваш профиль и показывать его работодателям. Профиль останется, но будет скрыт.', ok: 'Отозвать', danger: true });
        if (!ok) { fill(); return; }
      }
      busyC.value = true;
      try { store.me = await api.post('/candidates/me/consents', { processing: consents.processing, publication: consents.publication }); fill(); toast('Согласия сохранены', 'ok'); }
      catch (e) { toast(e.detail, 'err'); fill(); } finally { busyC.value = false; }
    }
    async function savePrivacy() {
      busyP.value = true;
      try { store.me = await api.put('/candidates/me/privacy', { ...privacy }); fill(); toast('Настройки приватности сохранены', 'ok'); }
      catch (e) { toast(e.detail, 'err'); fill(); } finally { busyP.value = false; }
    }
    const rows = [
      { k: 'visible_to_employers', title: 'Показывать профиль в подборках и банке кандидатов', text: 'Выключите, если временно не ищете работу. Приглашения перестанут приходить.' },
      { k: 'achievements', title: 'Достижения ФСП', text: 'Работодатель видит записи профиля достижений и их уровень доверия.' },
      { k: 'fsp_link', title: 'Отметка о связи с ФСП ID', text: 'Показывать, что профиль связан с ФСП ID (сам идентификатор не раскрывается).' },
      { k: 'city', title: 'Город', text: 'Нужен для подбора по месту работы.' },
      { k: 'salary', title: 'Зарплатные ожидания', text: 'Помогают работодателю предложить подходящие условия.' },
    ];
    return { me, consents, privacy, rows, saveConsents, savePrivacy, busyC, busyP };
  },
  template: `
    <PageHead title="Настройки" sub="Что о вас видит работодатель до принятия приглашения и на что вы даёте согласие." />
    <div class="grid grid-2" style="align-items:start">
      <div class="card">
        <h2>Согласия</h2>
        <label class="check" :class="{ on: consents.processing }"><input type="checkbox" v-model="consents.processing" @change="saveConsents" :disabled="busyC">
          <span><span class="check-title">Согласие на обработку персональных данных</span><br>
          <span class="check-text">Даю согласие оператору платформы «Карьера ФСП» на обработку моих персональных данных (ФИО, контакты, сведения об опыте, результаты тестирования, достижения) в целях подбора работы, включая хранение и систематизацию, в соответствии с Федеральным законом № 152-ФЗ. Согласие действует до отзыва.</span></span></label>
        <label class="check" :class="{ on: consents.publication }" style="margin-top:10px"><input type="checkbox" v-model="consents.publication" @change="saveConsents" :disabled="busyC || !consents.processing">
          <span><span class="check-title">Согласие на показ профиля работодателям</span><br>
          <span class="check-text">Разрешаю показывать зарегистрированным работодателям обезличенный профиль: псевдоним «Кандидат № …», категорию, стек, результаты теста, достижения и выбранные ниже поля. ФИО и контакты раскрываются только после того, как я приму приглашение или откликнусь на вакансию.</span></span></label>
        <p v-if="!consents.processing" class="muted" style="font-size:13px;margin-top:10px">Согласие на показ можно дать только вместе с согласием на обработку.</p>
      </div>
      <div class="card">
        <h2>Приватность: что видит работодатель</h2>
        <div class="switch-row" v-for="r in rows" :key="r.k">
          <div><div style="font-weight:600;color:var(--violet);font-size:14px">{{ r.title }}</div><div class="muted" style="font-size:13px">{{ r.text }}</div></div>
          <label class="switch"><input type="checkbox" v-model="privacy[r.k]" @change="savePrivacy" :disabled="busyP"><span class="knob"></span></label>
        </div>
        <p class="muted" style="font-size:12.5px;margin:12px 0 0">Всегда скрыты до вашего согласия: ФИО, телефон, Telegram, почта. Всегда видны: псевдоним, категория, стек с отметками теста.</p>
      </div>
    </div>`,
};
