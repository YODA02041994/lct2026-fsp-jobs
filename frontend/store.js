/* Общее состояние: вход, справочник, профиль, уведомления, подтверждения. */
import { reactive } from 'vue';
import { api, auth, onUnauthorized } from './api.js';
import { navigate } from './router.js';

export const store = reactive({
  token: auth.token,
  role: auth.role,
  user: null,          // GET /auth/me
  me: null,            // профиль кандидата или компании
  catalog: null,       // GET /catalog
  ready: false,        // справочник и пользователь загружены
  toasts: [],
  confirm: null,       // { title, text, ok, cancel, danger, resolve }
});

let toastSeq = 0;
export function toast(text, type = 'ok', ms = 4200) {
  const id = ++toastSeq;
  store.toasts.push({ id, text, type });
  setTimeout(() => { store.toasts = store.toasts.filter((t) => t.id !== id); }, ms);
}

export function confirmDialog({ title = 'Подтвердите действие', text = '', ok = 'Подтвердить', cancel = 'Отмена', danger = false } = {}) {
  return new Promise((resolve) => { store.confirm = { title, text, ok, cancel, danger, resolve }; });
}
export function closeConfirm(result) {
  if (store.confirm) { store.confirm.resolve(result); store.confirm = null; }
}

export async function loadCatalog() {
  if (!store.catalog) store.catalog = await api.get('/catalog');
  return store.catalog;
}

export async function loadMe() {
  if (!store.token) { store.user = null; store.me = null; return null; }
  store.user = await api.get('/auth/me');
  store.role = store.user.role;
  store.me = store.role === 'candidate' ? await api.get('/candidates/me') : await api.get('/employers/me');
  return store.me;
}

export async function refreshMe() {
  if (!store.token) return null;
  store.me = store.role === 'candidate' ? await api.get('/candidates/me') : await api.get('/employers/me');
  return store.me;
}

export function setSession(token, role) {
  auth.set(token, role);
  store.token = token;
  store.role = role;
}

export function logout(silent = false) {
  auth.clear();
  store.token = ''; store.role = ''; store.user = null; store.me = null;
  if (!silent) toast('Вы вышли из системы');
  navigate('/login');
}

onUnauthorized(() => {
  store.token = ''; store.role = ''; store.user = null; store.me = null;
  toast('Сеанс завершён. Войдите снова', 'warn');
  navigate('/login');
});

export function homeFor(role) { return role === 'employer' ? '/employer' : '/candidate'; }

/* ---- подписи из справочника ---- */
export function specName(code) {
  const s = store.catalog && store.catalog.specializations.find((x) => x.code === code);
  return s ? s.name : (code || '—');
}
export function gradeTitle(code) {
  const g = store.catalog && store.catalog.grades.find((x) => x.code === code);
  return g ? g.title : (code || '—');
}
export function gradeDesc(code) {
  const g = store.catalog && store.catalog.grades.find((x) => x.code === code);
  return g ? g.description : '';
}
export function formatTitle(code) {
  const f = store.catalog && store.catalog.work_formats.find((x) => x.code === code);
  return f ? f.title : (code || '—');
}
export function skillName(code) {
  const s = store.catalog && store.catalog.skills.find((x) => x.code === code);
  return s ? s.name : code;
}
export function categoryTitle(spec, grade) {
  if (!spec || !grade) return 'Категория не определена';
  return `${specName(spec)} · ${gradeTitle(grade)}`;
}
export const WEIGHT_TITLES = { stack: 'Стек', grade: 'Грейд', strength: 'Сила профиля', fsp: 'Достижения ФСП', activity: 'Актуальность', conditions: 'Условия' };
export function skillCode(nameOrCode) {
  const v = String(nameOrCode || '').trim();
  const s = store.catalog && store.catalog.skills.find((x) => x.code === v.toLowerCase() || x.name.toLowerCase() === v.toLowerCase());
  return s ? s.code : v;
}
export const CONTACT_METHODS = ['Telegram', 'Почта', 'Телефон', 'Видеозвонок'];
