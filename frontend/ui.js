/* Общие элементы интерфейса и форматирование. */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { store, WEIGHT_TITLES, skillName } from './store.js';

/* ---------- форматирование ---------- */
const rub = new Intl.NumberFormat('ru-RU');
export function money(n) {
  if (n === null || n === undefined || n === '') return '—';
  return `${rub.format(Math.round(Number(n)))} ₽`;
}
export function moneyRange(min, max) {
  if ((min === null || min === undefined) && (max === null || max === undefined)) return 'зарплата не указана';
  if (min !== null && min !== undefined && max !== null && max !== undefined) return `${rub.format(min)} – ${rub.format(max)} ₽`;
  if (min !== null && min !== undefined) return `от ${rub.format(min)} ₽`;
  return `до ${rub.format(max)} ₽`;
}
export function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}
export function fmtDateShort(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
export function fmtDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}
export function pct(x) { return `${Math.round((Number(x) || 0) * 100)} %`; }
export function plural(n, one, few, many) {
  const a = Math.abs(n) % 100; const b = a % 10;
  if (a > 10 && a < 20) return many;
  if (b > 1 && b < 5) return few;
  if (b === 1) return one;
  return many;
}
export function futureOrPast(iso) { return iso && new Date(iso).getTime() > Date.now(); }

export const STATUS = {
  sent: { label: 'отправлено', cls: 'st-sent' },
  viewed: { label: 'просмотрено', cls: 'st-viewed' },
  accepted: { label: 'принято', cls: 'st-accepted' },
  declined: { label: 'отклонено', cls: 'st-declined' },
  active: { label: 'идёт', cls: 'st-viewed' },
  finished: { label: 'завершён', cls: 'st-accepted' },
  expired: { label: 'истёк срок', cls: 'st-declined' },
  revoked: { label: 'отозвано', cls: 'st-declined' },
  open: { label: 'открыта', cls: 'st-accepted' },
  closed: { label: 'закрыта', cls: 'st-declined' },
};
export const TRUST = {
  source: { label: 'подтверждено источником', cls: 'trust-source', hint: 'Запись получена из реестра ФСП по связанному ФСП ID' },
  document: { label: 'по документу', cls: 'trust-document', hint: 'Подтверждено загруженным документом (приказ, диплом, зачётная книжка)' },
  claimed: { label: 'заявлено', cls: 'trust-claimed', hint: 'Указано самим кандидатом, без подтверждения' },
};
export const DECISION = {
  confirmed: 'Грейд подтверждён',
  suggest_lower: 'Рекомендуем попробовать уровень ниже',
  suggest_higher: 'Уверенный результат — можно повысить грейд',
};

/* ---------- загрузка данных ---------- */
export function useLoad(fn, { immediate = true } = {}) {
  const data = ref(null);
  const loading = ref(false);
  const error = ref('');
  async function reload(...args) {
    loading.value = true; error.value = '';
    try { data.value = await fn(...args); }
    catch (e) { error.value = e.detail || e.message || 'Ошибка'; }
    finally { loading.value = false; }
    return data.value;
  }
  if (immediate) onMounted(() => reload());
  return { data, loading, error, reload };
}

/* ---------- элементы ---------- */
export const Spinner = { template: `<span class="spinner" aria-label="Загрузка"></span>` };

export const Loader = {
  props: { loading: Boolean, error: String, empty: Boolean, emptyTitle: { type: String, default: 'Пока пусто' }, emptyHint: String },
  emits: ['retry'],
  template: `
    <div v-if="loading" class="state"><span class="spinner"></span> Загрузка…</div>
    <div v-else-if="error" class="state state-error">
      <div><strong>Не получилось загрузить.</strong> {{ error }}</div>
      <button class="btn btn-ghost" type="button" @click="$emit('retry')">Повторить</button>
    </div>
    <div v-else-if="empty" class="empty">
      <div class="empty-icon">○</div>
      <div class="empty-title">{{ emptyTitle }}</div>
      <div v-if="emptyHint" class="empty-hint">{{ emptyHint }}</div>
      <slot name="empty"></slot>
    </div>
    <slot v-else></slot>`,
};

export const StatusBadge = {
  props: { status: String },
  computed: { s() { return STATUS[this.status] || { label: this.status || '—', cls: '' }; } },
  template: `<span class="badge" :class="s.cls">{{ s.label }}</span>`,
};

export const TrustBadge = {
  props: { level: String },
  computed: { t() { return TRUST[this.level] || { label: this.level, cls: '', hint: '' }; } },
  template: `<span class="badge trust" :class="t.cls" :title="t.hint">{{ t.label }}</span>`,
};

export const Tag = {
  props: { confirmed: Boolean, score: [Number, String], muted: Boolean, removable: Boolean },
  emits: ['remove'],
  template: `<span class="tag" :class="{ 'tag-confirmed': confirmed, 'tag-muted': muted }"
      :title="confirmed ? 'Подтверждено тестом' + (score !== undefined && score !== null ? ': ' + Math.round(score * 100) + ' %' : '') : ''">
      <slot></slot><span v-if="confirmed" class="tag-check" aria-hidden="true">✓</span>
      <button v-if="removable" type="button" class="tag-x" @click="$emit('remove')" aria-label="Убрать">×</button></span>`,
};

export const Modal = {
  props: { title: String, wide: Boolean },
  emits: ['close'],
  mounted() { this.onKey = (e) => { if (e.key === 'Escape') this.$emit('close'); }; document.addEventListener('keydown', this.onKey); document.body.classList.add('no-scroll'); },
  beforeUnmount() { document.removeEventListener('keydown', this.onKey); document.body.classList.remove('no-scroll'); },
  template: `
    <div class="modal-back" @click.self="$emit('close')">
      <div class="modal" :class="{ wide }" role="dialog" aria-modal="true">
        <div class="modal-head"><h3>{{ title }}</h3><button type="button" class="icon-btn" @click="$emit('close')" aria-label="Закрыть">×</button></div>
        <div class="modal-body"><slot></slot></div>
        <div v-if="$slots.footer" class="modal-foot"><slot name="footer"></slot></div>
      </div>
    </div>`,
};

export const Field = {
  props: { label: String, hint: String, required: Boolean, error: String },
  template: `
    <label class="field">
      <span class="field-label">{{ label }}<span v-if="required" class="req" title="Обязательное поле"> *</span></span>
      <slot></slot>
      <span v-if="error" class="field-error">{{ error }}</span>
      <span v-else-if="hint" class="field-hint">{{ hint }}</span>
    </label>`,
};

/* Зарплата «от – до»: два числовых поля, проверка от ≤ до. v-model = { min, max } */
export const MoneyRange = {
  props: { modelValue: { type: Object, default: () => ({ min: null, max: null }) }, required: Boolean, label: { type: String, default: 'Зарплата в месяц, ₽' } },
  emits: ['update:modelValue'],
  computed: {
    err() {
      const { min, max } = this.modelValue;
      if (min !== null && min !== '' && max !== null && max !== '' && Number(min) > Number(max)) return '«От» больше, чем «до»';
      return '';
    },
  },
  methods: {
    set(k, v) { this.$emit('update:modelValue', { ...this.modelValue, [k]: v === '' ? null : Number(v) }); },
  },
  template: `
    <div class="field">
      <span class="field-label">{{ label }}<span v-if="required" class="req"> *</span></span>
      <div class="money-range">
        <input type="number" inputmode="numeric" min="0" step="1000" placeholder="от" :value="modelValue.min" @input="set('min', $event.target.value)" :required="required">
        <span class="dash">—</span>
        <input type="number" inputmode="numeric" min="0" step="1000" placeholder="до" :value="modelValue.max" @input="set('max', $event.target.value)" :required="required">
      </div>
      <span v-if="err" class="field-error">{{ err }}</span>
      <span v-else class="field-hint">Целые рубли в месяц, до вычета налогов</span>
    </div>`,
};

/* Ввод набора значений тегами: v-model = массив строк; подсказки — из справочника навыков */
export const TagsInput = {
  props: { modelValue: { type: Array, default: () => [] }, placeholder: { type: String, default: 'введите и нажмите Enter' }, suggestions: { type: Array, default: () => [] }, listId: String },
  emits: ['update:modelValue'],
  data() { return { text: '' }; },
  computed: { id() { return this.listId || 'dl-' + Math.random().toString(36).slice(2, 8); } },
  methods: {
    add() {
      const parts = this.text.split(/[,;]+/).map((s) => s.trim()).filter(Boolean);
      const next = [...this.modelValue];
      parts.forEach((p) => { if (!next.some((x) => x.toLowerCase() === p.toLowerCase())) next.push(p); });
      this.$emit('update:modelValue', next); this.text = '';
    },
    remove(i) { const next = [...this.modelValue]; next.splice(i, 1); this.$emit('update:modelValue', next); },
    onKey(e) { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); this.add(); } else if (e.key === 'Backspace' && !this.text && this.modelValue.length) this.remove(this.modelValue.length - 1); },
  },
  template: `
    <div class="tags-input" @click="$refs.inp.focus()">
      <span v-for="(t, i) in modelValue" :key="t" class="tag"><slot name="tag" :value="t">{{ t }}</slot><button type="button" class="tag-x" @click.stop="remove(i)" aria-label="Убрать">×</button></span>
      <input ref="inp" v-model="text" :placeholder="modelValue.length ? '' : placeholder" @keydown="onKey" @blur="add" :list="suggestions.length ? id : null">
      <datalist v-if="suggestions.length" :id="id"><option v-for="s in suggestions" :key="s" :value="s"></option></datalist>
    </div>`,
};

export const PageHead = {
  props: { title: String, sub: String },
  template: `<div class="page-head"><div><h1>{{ title }}</h1><p v-if="sub" class="sub">{{ sub }}</p></div><div class="page-actions"><slot></slot></div></div>`,
};

/* Полоски шести слагаемых оценки с весами из справочника */
export const ScoreParts = {
  props: { parts: Object, weights: Object, compact: Boolean },
  computed: {
    rows() {
      const w = this.weights || (store.catalog && store.catalog.weights) || {};
      return Object.keys(WEIGHT_TITLES).map((k) => ({ k, title: WEIGHT_TITLES[k], v: Number((this.parts || {})[k] || 0), w: w[k] }));
    },
  },
  template: `
    <div class="parts" :class="{ compact }">
      <div v-for="r in rows" :key="r.k" class="part" :title="r.title + ': ' + Math.round(r.v * 100) + ' из 100' + (r.w !== undefined ? ', вес ' + r.w : '')">
        <span class="part-title">{{ r.title }}<small v-if="r.w !== undefined && !compact"> · вес {{ r.w }}</small></span>
        <span class="bar"><span class="bar-fill" :style="{ width: Math.round(r.v * 100) + '%' }"></span></span>
        <span class="part-val">{{ Math.round(r.v * 100) }}</span>
      </div>
    </div>`,
};

/* Карточка задания теста: показ вопроса и ввод ответа по формату (exact / choice / multichoice). */
export const TestItemView = {
  props: { payload: Object, modelValue: null, readonly: Boolean },
  emits: ['update:modelValue'],
  computed: {
    techs() { return (this.payload.technologies || []).map((t) => skillName(t)).filter((n) => n.toLowerCase() !== String(this.payload.competency || '').toLowerCase()); },
    multi: {
      get() { return Array.isArray(this.modelValue) ? this.modelValue : []; },
      set(v) { this.$emit('update:modelValue', v); },
    },
  },
  methods: { toggle(i) { const s = new Set(this.multi); s.has(i) ? s.delete(i) : s.add(i); this.multi = [...s].sort((a, b) => a - b); } },
  template: `
    <div class="test-item">
      <div class="test-item-meta">
        <span class="chip">{{ payload.title }}</span>
        <span class="chip chip-muted">{{ payload.competency }}</span>
        <span v-for="t in techs" :key="t" class="chip chip-tech">{{ t }}</span>
      </div>
      <p class="question">{{ payload.question }}</p>
      <pre v-if="payload.code" class="code" :data-lang="payload.language || ''"><code>{{ payload.code }}</code></pre>
      <div v-if="payload.format === 'exact'" class="answer">
        <label class="field"><span class="field-label">Ваш ответ</span>
          <input type="text" :value="modelValue ?? ''" :readonly="readonly" @input="$emit('update:modelValue', $event.target.value)" placeholder="точное значение" autocomplete="off"></label>
      </div>
      <div v-else-if="payload.format === 'choice'" class="answer options">
        <label v-for="(o, i) in payload.options" :key="i" class="option" :class="{ selected: modelValue === i }">
          <input type="radio" :name="'opt-' + payload.title" :value="i" :checked="modelValue === i" :disabled="readonly" @change="$emit('update:modelValue', i)"><span>{{ o }}</span></label>
      </div>
      <div v-else-if="payload.format === 'multichoice'" class="answer options">
        <p class="hint">Можно выбрать несколько вариантов</p>
        <label v-for="(o, i) in payload.options" :key="i" class="option" :class="{ selected: multi.includes(i) }">
          <input type="checkbox" :checked="multi.includes(i)" :disabled="readonly" @change="toggle(i)"><span>{{ o }}</span></label>
      </div>
    </div>`,
};

/* Обратный отсчёт по заданию */
export function useCountdown(onExpire) {
  const left = ref(0);
  let timer = null;
  function start(seconds) {
    stop();
    left.value = Math.max(0, Math.floor(seconds));
    if (left.value === 0) { onExpire && onExpire(); return; }
    timer = setInterval(() => {
      left.value -= 1;
      if (left.value <= 0) { stop(); onExpire && onExpire(); }
    }, 1000);
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  onBeforeUnmount(stop);
  const text = computed(() => `${String(Math.floor(left.value / 60)).padStart(1, '0')}:${String(left.value % 60).padStart(2, '0')}`);
  return { left, text, start, stop };
}

export const components = { Spinner, Loader, StatusBadge, TrustBadge, Tag, Modal, Field, MoneyRange, TagsInput, PageHead, ScoreParts, TestItemView };
