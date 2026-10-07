# Контракт API v1 (для фронтенда и документации)

База: `{PREFIX}/api/v1`, где `PREFIX` — `""` локально или `/fsp` на стенде (фронтенд берёт его из `window.APP_PREFIX`
или вычисляет из своего адреса). Все ответы — JSON. Ошибки: `{"detail": "текст на русском"}` с кодами 400/401/403/404/409/422.
Авторизация: заголовок `Authorization: Bearer <token>`. Даты — ISO 8601. Деньги — целые рубли в месяц.

## Справочники (без входа)
- `GET /catalog` → `{specializations:[{code,name,description,has_bank}], grades:[{code,title,description}], work_formats:[{code,title}], skills:[{code,name,group}], weights:{stack,grade,strength,fsp,activity,conditions}, test:{block_size,blocks,item_seconds}, demo_mode:bool}`

## Аутентификация
- `POST /auth/register` `{email,password,role:"candidate"|"employer"}` → `{user_id, email, role, confirm_required:true, demo_confirm_url?:string}` (ссылка возвращается только в демонстрационном режиме без SMTP)
- `GET /auth/confirm?token=…` → `{ok:true, access_token, role}` (подтверждает почту и сразу входит)
- `POST /auth/login` `{email,password}` → `{access_token, role, user_id}`; 403 если почта не подтверждена
- `GET /auth/me` → `{user_id,email,role,email_confirmed}`

## Кандидат (`role=candidate`)
- `GET /candidates/me` → профиль: `{id, alias, full_name, phone, telegram, city, experience_years, roles[], soft_skills[], about, salary_min, salary_max, work_format, specialization_code, claimed_grade, grade, grade_changed_at, grade_change_available_at, fsp_id, fsp_linked_at, visible_to_employers, privacy:{achievements,city,salary,fsp_link}, consents:{processing:bool,publication:bool}, skills:[{skill,name,source,confirmed_by_test,test_score}], category:{specialization,grade,title}|null, last_test:{...}|null}`
- `PUT /candidates/me` — любые поля профиля из списка выше (кроме grade/alias/fsp*/skills) + `skills:[string]` (строки нормализуются по словарю, неизвестные сохраняются как есть)
- `PUT /candidates/me/privacy` `{achievements,city,salary,fsp_link, visible_to_employers}` → профиль
- `POST /candidates/me/consents` `{processing:bool, publication:bool}` → профиль
- `POST /candidates/me/resume` — multipart `file` (PDF) → `{parsed:{full_name,phone,telegram,city,experience_years,skills[],roles[],soft_skills[],about}, applied:bool}` (поля предзаполняются, но не перезаписывают уже заполненные без `?apply=1`)
- `GET /candidates/me/profile.pdf` → PDF стандартизированного профиля
- `GET /candidates/me/achievements` → `[{id,kind,title,discipline,level_code,place,date,valid_until,trust_level,status,hidden,event:{name,ekp_number,level}|null}]`
- `POST /candidates/me/achievements` `{kind,title,discipline,date,place?,document_name?}` → запись со `trust_level:"claimed"`
- `PATCH /candidates/me/achievements/{id}` `{hidden:bool}`
- ФСП ID: `GET /fsp/link/start` → `{redirect_url}`; пользователь уходит на издателя; издатель возвращает на `GET /fsp/callback?code=…&state=…` → редирект на фронтенд `#/candidate/profile?fsp=linked`; `POST /fsp/unlink` → профиль. Демонстрационный издатель: `GET /fsp/mock/login?state=…` — страница с выбором тестового участника.
- Тест:
  - `GET /tests/options` → `{specializations:[...], grades:[...], can_change_grade:bool, grade_change_available_at}`
  - `POST /tests/sessions` `{specialization_code, claimed_grade, declared_skills:[string]}` → `Session`
  - `GET /tests/sessions/{id}` → `Session`
  - `POST /tests/sessions/{id}/answer` `{item_id, answer}` → `{item_id, accepted:true, block_done:bool, session_status}` (правильность не раскрывается)
  - `POST /tests/sessions/{id}/next` → `Session` (следующий блок или финал)
  - `GET /tests/sessions` → история `[SessionShort]`
  - `POST /tests/sessions/{id}/apply` → применить предложенный грейд (повышение или понижение) → профиль
  - `Session = {id, status:"active"|"finished", specialization_code, claimed_grade, current_block, blocks_total, block_size, current_level, items:[{id, block_no, order_no, level, payload:{title,competency,technologies[],format,question,code,language,options[]}, answered:bool, seconds_left}], result:{theta, theta_sd, result_grade, decision:"confirmed"|"suggest_lower"|"suggest_higher", correct_total, items_total, by_technology:[{skill,name,correct,total}], can_apply:bool, grade_change_available_at}|null}`
- Приглашения: `GET /candidates/me/invitations` → `[{id, status, company_name, message, salary_min, salary_max, contact_method, vacancy:{id,title}|null, sent_at, viewed_at, responded_at}]`; `POST /invitations/{id}/view`; `POST /invitations/{id}/respond` `{decision:"accept"|"decline"}`
- Вакансии: `GET /vacancies?specialization&grade&skill&q` → `[{id,title,company_name,specialization_code,grade,stack[],salary_min,salary_max,work_format,city,created_at}]`; `GET /vacancies/{id}` → подробно `+description`; `POST /vacancies/{id}/apply` `{message}` → отклик; `GET /candidates/me/applications` → `[{id,vacancy:{id,title,company_name,salary_min,salary_max},status,created_at}]`
- Короткие задания: `GET /candidates/me/short-tasks` → `[{id,title,text,company_name,technologies[],answered:bool,employer_score}]`; `POST /short-tasks/{id}/answer` `{answer}`

## Работодатель (`role=employer`)
- `GET /employers/me`, `PUT /employers/me` `{company_name,description,industry,website,city,contact_person,contact_email,contact_phone}`
- Потребность и подборка:
  - `POST /needs` `{title,text,specialization_code?,grade?,stack?[],salary_min?,salary_max?,work_format?,city?}` → `{need, extracted:{specialization_code,grade,stack[],salary_min,salary_max,source}}` (из текста извлекаются технологии, грейд, специализация и зарплата; `source` = `rules` или `rules+model` — правила, затем внешняя модель по обезличенному тексту; явные поля главнее)
  - `GET /needs` → список
  - `POST /needs/{id}/selection` `{weights?}` → `Selection`
  - `POST /selections/{id}/refine` `{filters:{specialization_code?,grades?[],skills?[],fsp_only?:bool,city?,salary_max?}, weights?}` → `Selection` (новая версия; прежние сохраняются)
  - `GET /selections/{id}` → `Selection`; `GET /selections` → список
  - `Selection = {id, need_id, versions:[{version_no, filters, weights, created_at, categories:[{specialization_code,grade,title,count,avg_score}], results:[CandidateCard]}]}`
  - `CandidateCard = {candidate_id, alias, category:{specialization_code,grade,title}, score (калиброванная оценка 0…1: вероятность, что кандидат подходит; без потребности — сырой итог), raw_score (сырой итог формулы 0…1), parts:{stack,grade,strength,fsp,activity,conditions}, explanation, skills:[{skill,name,confirmed_by_test}], achievements_summary:string, fsp_linked:bool, city?, salary_min?, salary_max?, work_format?, contacts_unlocked:bool, contacts?:{full_name,phone,telegram,email}}`
- Банк кандидатов: `GET /candidates/search?specialization_code&grade&skills=a,b&fsp_only=1&q=` → `[CandidateCard]` (та же формула с нулевыми слагаемыми потребности)
- `GET /candidates/{id}/card` → `CandidateCard` (контакты только если `contacts_unlocked`)
- Приглашения: `POST /invitations` `{candidate_id, message, salary_min, salary_max, contact_method, vacancy_id?, selection_version_id?}` → приглашение; `GET /employers/me/invitations` → `[{id,candidate:{candidate_id,alias},status,message,salary_min,salary_max,sent_at,viewed_at,responded_at,contacts?}]`
- Вакансии: `POST /vacancies`, `PUT /vacancies/{id}`, `GET /employers/me/vacancies`, `GET /vacancies/{id}/applications` → `[{id,candidate:CandidateCard,message,status,created_at}]`, `PATCH /applications/{id}` `{status:"viewed"|"accepted"|"declined"}`
- Короткие задания: `POST /short-tasks` `{title,text,specialization_code?,technologies?[]}`; `GET /employers/me/short-tasks` → `[{...,answers:[{candidate:{candidate_id,alias},answer,employer_score,created_at}]}]`; `PATCH /short-task-answers/{id}` `{employer_score}`
- Задания под вакансию: `GET /vacancies/{id}/test-preview` → `{technologies[], items:[payload]}` — показывает, как из описания формируются задания

## Правила видимости
- Контакты кандидата (`full_name, phone, telegram, email`) отдаются работодателю только при `contacts_unlocked` — после `accepted` приглашения этого работодателя или отклика кандидата на его вакансию. Открытие контактов пишется в журнал.
- До этого кандидат виден как `alias` («Кандидат № N») с категорией, навыками, достижениями (с учётом настроек приватности).

## Служебные адреса

- `GET /api/health` → `{status, templates, demo_mode, model}` — `templates` — число шаблонов в банке, `demo_mode` — нет SMTP (ссылка подтверждения показывается на экране), `model` — настроена ли внешняя модель для разбора текста.
- `GET /api/docs`, `GET /api/openapi.json` — интерактивная документация и схема.
