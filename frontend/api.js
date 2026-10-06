/* Доступ к API. Единственное место, где известны адреса и формат ошибок (docs/API_контракт.md). */

export const PREFIX = window.APP_PREFIX ?? (location.pathname.startsWith('/fsp') ? '/fsp' : '');
const BASE = `${PREFIX}/api/v1`;
const TOKEN_KEY = 'fsp_token';
const ROLE_KEY = 'fsp_role';

export class ApiError extends Error {
  constructor(status, detail, data) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY) || ''; },
  get role() { return localStorage.getItem(ROLE_KEY) || ''; },
  set(token, role) { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(ROLE_KEY, role); },
  clear() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(ROLE_KEY); },
};

const unauthorizedHandlers = [];
export function onUnauthorized(fn) { unauthorizedHandlers.push(fn); }

function detailText(data, status) {
  const d = data && data.detail;
  if (Array.isArray(d)) {                         // формат ошибок валидации FastAPI
    return d.map((e) => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`.replace(/^: /, '')).join('; ');
  }
  if (typeof d === 'string' && d) return d;
  const byStatus = { 400: 'Неверный запрос', 401: 'Нужно войти в систему', 403: 'Нет доступа', 404: 'Не найдено', 409: 'Конфликт данных', 422: 'Проверьте заполнение полей', 500: 'Ошибка сервера' };
  return byStatus[status] || `Ошибка ${status}`;
}

function buildQuery(query) {
  if (!query) return '';
  const p = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '' || v === false) return;
    p.set(k, Array.isArray(v) ? v.join(',') : v === true ? '1' : v);
  });
  const s = p.toString();
  return s ? `?${s}` : '';
}

export async function request(method, path, { body, query, form, blob } = {}) {
  const headers = {};
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;
  let payload;
  if (form) payload = form;                            // multipart: границу выставит браузер
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  let res;
  try {
    res = await fetch(`${BASE}${path}${buildQuery(query)}`, { method, headers, body: payload });
  } catch (e) {
    throw new ApiError(0, 'Сервер недоступен. Проверьте, что API запущен.', null);
  }
  if (res.status === 401 && auth.token && !path.startsWith('/auth/login')) {
    auth.clear();
    unauthorizedHandlers.forEach((fn) => fn());
  }
  if (blob) {
    if (!res.ok) {
      let data = null;
      try { data = await res.json(); } catch (_) { /* тело не JSON */ }
      throw new ApiError(res.status, detailText(data, res.status), data);
    }
    return await res.blob();
  }
  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch (_) { data = { detail: text.slice(0, 200) }; }
  }
  if (!res.ok) throw new ApiError(res.status, detailText(data, res.status), data);
  return data;
}

export const api = {
  get: (path, query) => request('GET', path, { query }),
  post: (path, body) => request('POST', path, { body }),
  put: (path, body) => request('PUT', path, { body }),
  patch: (path, body) => request('PATCH', path, { body }),
  upload: (path, form, query) => request('POST', path, { form, query }),
  blob: (path) => request('GET', path, { blob: true }),
};

/* Скачать файл, требующий заголовка Authorization (обычная ссылка его не передаст). */
export async function downloadFile(path, filename) {
  const b = await api.blob(path);
  const url = URL.createObjectURL(b);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.style.display = 'none';
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
}
