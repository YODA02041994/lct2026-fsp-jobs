/* Приглашения работодателя со статусами и контактами после принятия. */
import { ref, computed } from 'vue';
import { api } from '../../api.js';
import { useLoad, moneyRange, fmtDateTime } from '../../ui.js';

export const EmployerInvitations = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/employers/me/invitations'));
    const filter = ref('all');
    const list = computed(() => (data.value || []).filter((i) => filter.value === 'all' || (filter.value === 'open' ? ['sent', 'viewed'].includes(i.status) : i.status === filter.value)));
    const counts = computed(() => ({ all: (data.value || []).length, open: (data.value || []).filter((i) => ['sent', 'viewed'].includes(i.status)).length, accepted: (data.value || []).filter((i) => i.status === 'accepted').length, declined: (data.value || []).filter((i) => i.status === 'declined').length }));
    return { data, list, loading, error, reload, filter, counts, moneyRange, fmtDateTime };
  },
  template: `
    <PageHead title="Приглашения" sub="Статусы: отправлено → просмотрено → принято или отклонено. Контакты кандидата появляются здесь после принятия." />
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Приглашений ещё нет" empty-hint="Соберите подборку по потребности или откройте банк кандидатов и нажмите «Пригласить» у подходящего кандидата." @retry="reload">
      <template #empty><a href="#/employer/needs" class="btn btn-primary">К подборкам</a></template>
      <div class="tabs">
        <button type="button" :class="{ active: filter === 'all' }" @click="filter = 'all'">Все ({{ counts.all }})</button>
        <button type="button" :class="{ active: filter === 'open' }" @click="filter = 'open'">Ждут ответа ({{ counts.open }})</button>
        <button type="button" :class="{ active: filter === 'accepted' }" @click="filter = 'accepted'">Принятые ({{ counts.accepted }})</button>
        <button type="button" :class="{ active: filter === 'declined' }" @click="filter = 'declined'">Отклонённые ({{ counts.declined }})</button>
      </div>
      <div class="list">
        <div v-for="i in list" :key="i.id" class="item">
          <div class="row-between">
            <div>
              <div class="item-title">{{ i.candidate.alias }} <StatusBadge :status="i.status" style="margin-left:6px" /></div>
              <div class="item-meta"><span v-if="i.vacancy">вакансия: {{ i.vacancy.title }}</span><span v-else>без привязки к вакансии</span><span v-if="i.contact_method">связь: {{ i.contact_method }}</span></div>
            </div>
            <div class="price big">{{ moneyRange(i.salary_min, i.salary_max) }}</div>
          </div>
          <p class="muted" style="margin:8px 0;font-size:14px">{{ i.message }}</p>
          <div class="timeline">
            <span class="t done"><span class="dot"></span>отправлено {{ fmtDateTime(i.sent_at) }}</span>
            <span class="t" :class="{ done: i.viewed_at }"><span class="dot"></span>просмотрено {{ i.viewed_at ? fmtDateTime(i.viewed_at) : '' }}</span>
            <span class="t" :class="{ done: i.responded_at }"><span class="dot"></span>{{ i.status === 'declined' ? 'отклонено' : 'принято' }} {{ i.responded_at ? fmtDateTime(i.responded_at) : '' }}</span>
          </div>
          <div v-if="i.status === 'accepted' && i.contacts" class="contacts" style="margin-top:10px">
            <strong>Кандидат принял приглашение — контакты открыты</strong>
            <dl class="kv" style="margin-top:4px"><dt>ФИО</dt><dd>{{ i.contacts.full_name || '—' }}</dd><dt>Телефон</dt><dd>{{ i.contacts.phone || '—' }}</dd><dt>Telegram</dt><dd>{{ i.contacts.telegram || '—' }}</dd><dt>Почта</dt><dd>{{ i.contacts.email || '—' }}</dd></dl>
          </div>
          <div v-else-if="i.status === 'accepted'" class="note note-ok" style="margin:10px 0 0">Принято. Контакты доступны в карточке кандидата.</div>
        </div>
        <div v-if="!list.length" class="empty"><div class="empty-title">В этой группе пусто</div></div>
      </div>
    </Loader>`,
};
