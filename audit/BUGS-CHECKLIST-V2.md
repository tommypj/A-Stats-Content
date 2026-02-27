# A-Stats-Online: Full App Audit — Bugs Checklist V2

**Date**: 2026-02-27
**Scope**: Post-fix re-audit of all 10 sections (backend + frontend)
**Total Issues Found**: ~277 across 10 audit sections

---

## Severity Key
- 🔴 **Critical** — Security vulnerability or data-loss risk; fix immediately
- 🟠 **High** — Major functional bug or security weakness; fix in next sprint
- 🟡 **Medium** — Logic error, edge case, or moderate risk; fix soon
- 🟢 **Low** — Code quality, performance, or UX improvement; fix when possible

---

## Quick Summary Table

| Section | Critical | High | Medium | Low | Total |
|---------|----------|------|--------|-----|-------|
| AUTH & Project Mgmt | 1 | 7 | 13 | 10 | 31 |
| Content Generation | 2 | 11 | 12 | 5 | 30 |
| Billing | 1 | 7 | 9 | 4 | 21 |
| Analytics & KV | 4 | 8 | 10 | 8 | 30 |
| Social & Images | 1 | 10 | 17 | 6 | 34 |
| Agency/Admin/Bulk | 1 | 8 | 11 | 10 | 30 |
| Infrastructure & DB | 0 | 3 | 11 | 14 | 28 |
| FE Core & Auth | 4 | 9 | 10 | 7 | 30 |
| FE Content & Gen UI | 4 | 4 | 14 | 8 | 30 |
| FE Analytics/Social/Admin | 3 | 2 | 22 | 20 | 47 |
| **TOTAL** | **21** | **69** | **129** | **92** | **311** |

---

## Section 1: AUTH & Project Management

### AUTH Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| AUTH-19 | 🟡 | [ ] | `resend_verification` crashes if email service fails — no try/catch | auth.py | 575-579 |
| AUTH-20 | 🟢 | [ ] | `get_current_user()` — `IndexError` if header is exactly "Bearer" with no token | auth.py | 81 |
| AUTH-21 | 🟡 | [ ] | Password invalidation comparison direction inconsistent (`>` vs `<`) between `get_current_user` and `refresh_token` | auth.py | 118, 343 |
| AUTH-22 | 🟠 | [x] | If personal project not found during token validation, `current_project_id` set to None without creating one | auth.py | 140-150 |
| AUTH-23 | 🟡 | [ ] | Avatar upload trusts `content_type` header; no file magic-byte validation | auth.py | 723-735 |
| AUTH-24 | 🟡 | [ ] | Data export includes soft-deleted articles/outlines/images | auth.py | 797-870 |
| AUTH-25 | 🟡 | [ ] | Account deletion cascades are not atomic — partial failure leaves inconsistent state | auth.py | 636-698 |

### PROJECT Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| PROJ-25 | 🔴 | [x] | Schema allows role `"member"` but DB enum has `"editor"` — invitation inserts will fail | schemas/project.py | 189 |
| PROJ-26 | 🟠 | [x] | Can invite members to personal workspace (should be single-user only) | project_invitations.py | 172-284 |
| PROJ-27 | 🟠 | [x] | Race condition in member-limit check — two simultaneous invitations can both pass | project_invitations.py | 190 |
| PROJ-28 | 🟠 | [x] | `invitation.inviter.name` accessed without null check — AttributeError if inviter deleted | project_invitations.py | 451 |
| PROJ-29 | 🟢 | [ ] | `page` / `page_size` params lack `Query(ge=1)` validation — negative values possible | project_invitations.py | 98-99 |
| PROJ-30 | 🟡 | [ ] | `status_filter` string not validated against enum values | project_invitations.py | 97, 114-115 |
| PROJ-31 | 🟢 | [ ] | No logging/alerting for repeated invalid invitation token attempts | project_invitations.py | 410-456 |
| PROJ-32 | 🟡 | [ ] | `current_user: Optional[User]` is dead code — dependency never returns None | project_invitations.py | 464, 512 |
| PROJ-33 | 🟢 | [ ] | `require_project_admin` defined locally AND imported from `deps_project` — duplicate | project_invitations.py | 43-91 |
| PROJ-34 | 🟢 | [ ] | Invitation role not validated at insert point (only in schema) — no defensive check | project_invitations.py | 237-245 |
| PROJ-35 | 🟠 | [x] | `get_project` query doesn't filter `deleted_at IS NULL` — then manually checks in Python | projects.py | 429-500 |
| PROJ-36 | 🟢 | [ ] | Redundant in-Python filtering of soft-deleted members (already filtered by DB in places) | projects.py | 203-208 |
| PROJ-37 | 🟠 | [ ] | Ownership transfer doesn't prevent attacker from locking out original owner afterward | projects.py | 703-741 |
| PROJ-38 | 🟡 | [x] | `remove_member` doesn't verify project still exists/not-deleted | projects.py | 648-675 |
| PROJ-39 | 🟠 | [x] | `invitation.inviter.name/email` accessed without null check in list/send flows | project_invitations.py | 155-156, 282-283 |
| PROJ-40 | 🟡 | [x] | Removing a member doesn't clear their `current_project_id` if they were in that project | projects.py | 647-675 |
| PROJ-41 | 🟡 | [ ] | Project delete doesn't verify only one owner exists before deletion | projects.py | 551-592 |
| PROJ-42 | 🟡 | [x] | `update_brand_voice` TOCTOU: re-queries project after permission check | projects.py | 341-383 |
| PROJ-43 | 🟡 | [ ] | `UpdateMemberRoleRequest` has no role validator — invalid role can be stored | schemas/project.py | 393-396 |
| PROJ-44 | 🟢 | [ ] | `accept_invitation` rate limit (10/min) too high for token brute-force protection | project_invitations.py | 459 |
| PROJ-45 | 🟢 | [ ] | Accept invitation auto-sets `current_project_id` without user's consent | project_invitations.py | 560-562 |
| PROJ-46 | 🟡 | [x] | `get_content_filter()` uses Union type attribute access which will fail at runtime | deps_project.py | 36-84 |
| PROJ-47 | 🟢 | [ ] | Circular import workaround in `deps_project.py` — imports inside functions | deps_project.py | 283-358 |
| PROJ-48 | 🟡 | [x] | `require_project_admin/owner` don't check if user is active/not-suspended | deps_project.py | 433-492 |

---

## Section 2: Content Generation Pipeline

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| GEN-21 | 🔴 | [x] | `AIGenerationError` raised but never defined — NameError on empty AI response | anthropic_adapter.py | 429 |
| GEN-22 | 🟠 | [x] | Inconsistent singular/plural resource_type keys between check and increment | generation_tracker.py | 74, 214 |
| GEN-23 | 🟠 | [x] | `improve_article` counts against generation limit — likely unintended | articles.py | 1097-1107 |
| GEN-24 | 🟠 | [x] | Race condition in monthly usage reset — no atomic CAS, two requests can both reset | project_usage.py | 278-316 |
| GEN-25 | 🟡 | [ ] | `status` filter not validated against ContentStatus enum | outlines.py | 189-190 |
| GEN-26 | 🟠 | [x] | Duplicate `ContentStatus` import inside function body (already imported at module level) | articles.py | 44, 985 |
| GEN-27 | 🟡 | [x] | Outline section structure not validated before `generate_article()` | articles.py | 483-587 |
| GEN-28 | 🔴 | [ ] | Limit check and usage increment not atomic — race allows exceeding monthly quota | generation_tracker.py | 56-102 |
| GEN-29 | 🟠 | [x] | `regenerate_outline` doesn't call `reset_project_usage_if_needed()` before limit check | outlines.py | 552-596 |
| GEN-30 | 🟠 | [x] | TOCTOU in `improve_article` — concurrent requests both pass limit check | articles.py | 1097-1107 |
| GEN-31 | 🟡 | [ ] | Hardcoded 60s timeout on `proofread_grammar` — not configurable | articles.py | 372-378 |
| GEN-32 | 🟠 | [x] | On generation failure, main session not explicitly rolled back before error session | articles.py | 450-465 |
| GEN-33 | 🟡 | [x] | No max section count validation — AI can return 50+ sections unchecked | anthropic_adapter.py | 265-273 |
| GEN-34 | 🟢 | [ ] | Keyword length not enforced before interpolation into AI prompts | anthropic_adapter.py | 206 |
| GEN-35 | 🟡 | [ ] | `log_start()` has no try/catch — DB error orphans generation task | generation_tracker.py | 27-48 |
| GEN-36 | 🟢 | [ ] | Usage counters use `or 0` — type mismatch (e.g., string) would cause silent failure | project_usage.py | 202 |
| GEN-37 | 🟡 | [x] | Export endpoints load all records into memory — OOM risk for large datasets | outlines.py | 214-255 |
| GEN-38 | 🟡 | [x] | `escape_like()` not audited — SQL injection risk if implementation is flawed | outlines.py | 192 |
| GEN-39 | 🟢 | [ ] | `meta_description` stored without length validation — max 160 chars not enforced | articles.py | 215-268 |
| GEN-40 | 🟠 | [ ] | Log truncation on JSON parse failure not applied consistently | articles.py | 751-755 |
| GEN-41 | 🟠 | [ ] | Per-user rate limiting missing — 100 users × 5 concurrent = 500 AI API calls | articles.py | 55 |
| GEN-42 | 🟠 | [x] | `restore_article_revision` — lacks explicit check that revision belongs to this article | articles.py | 1527-1535 |
| GEN-43 | 🟢 | [ ] | Outline regeneration allows keyword change (can cause confusion) | outlines.py | 552-678 |
| GEN-44 | 🟡 | [ ] | Session not wrapped in try/finally — potential session leak on outline creation error | outlines.py | 95-161 |
| GEN-45 | 🟢 | [ ] | `tone` and `target_audience` lack max length validation — prompt injection risk | outlines.py | 68-70 |
| GEN-46 | 🟡 | [ ] | Atomic increment in `project_usage.py` doesn't set reset_date on first write | project_usage.py | 259-274 |
| GEN-47 | 🟡 | [ ] | `writing_style`, `voice`, `list_usage` not validated against enum values | articles.py | 576-578 |
| GEN-48 | 🟢 | [ ] | `BulkJobItem` status field not validated against allowed enum values at creation | bulk.py | 68-77 |
| GEN-49 | 🟡 | [x] | Anthropic client timeout (300s) is hardcoded — not configurable | anthropic_adapter.py | 68-73 |
| GEN-50 | 🟡 | [x] | Keyword suggestion endpoint can generate 1000 AI calls/min at 10 req/min × 100 users | articles.py | 698-761 |

---

## Section 3: Billing & Subscriptions

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| BILL-17 | 🔴 | [x] | Checkout URL builds via f-string with user email — URL parameter injection | billing.py | 181-184 |
| BILL-18 | 🟠 | [ ] | Project webhook handler missing `with_for_update()` — race condition on concurrent webhooks | billing.py | 300 |
| BILL-19 | 🟠 | [ ] | Webhook idempotency degrades silently without Redis — duplicate events can double-charge | billing.py | 485-487 |
| BILL-20 | 🟠 | [ ] | User webhook lacks SERIALIZABLE isolation — concurrent updates can lose changes | billing.py | 534-662 |
| BILL-21 | 🟠 | [x] | `subscription_status` accepted from LemonSqueezy payload without validation vs enum | billing.py | 505, 566 |
| BILL-22 | 🟠 | [x] | Unknown `variant_id` silently downgrades to free without alerting — masks errors | billing.py | 308-325, 542-559 |
| BILL-23 | 🟡 | [ ] | User/project tier sync skipped silently if personal project missing | billing.py | 643-659 |
| BILL-24 | 🟡 | [x] | Webhook doesn't require non-null `subscription_id` / `customer_id` for paid events | billing.py | 502-506 |
| BILL-25 | 🟡 | [x] | `cancel_subscription` doesn't check subscription status before calling LS API | billing.py | 238-268 |
| BILL-26 | 🟡 | [ ] | Webhook endpoint has no rate limiting — DDoS vector | billing.py | 421-426 |
| BILL-27 | 🟡 | [ ] | SUBSCRIPTION_CANCELLED doesn't set `project.subscription_status = "cancelled"` | billing.py | 356-361 |
| BILL-28 | 🟡 | [x] | `lemonsqueezy_subscription_id` set to None if missing — corrupt paid records | billing.py | 334, 568 |
| BILL-29 | 🟡 | [ ] | `renews_at` / `subscription_expires` not validated to be in the future | billing.py | Multiple |
| BILL-30 | 🟡 | [x] | `create_project_checkout` accepts arbitrary `variant_id` without validation | project_billing.py | 169-220 |
| BILL-31 | 🟡 | [x] | Malformed `renews_at` silently skips expiry update — subscription never expires | billing.py | 337-338 |
| BILL-32 | 🟢 | [ ] | Free plan exclusion hardcoded — not derived from PLANS dict, brittle to additions | billing.py | 154-158 |
| BILL-33 | 🟢 | [ ] | Minimal logging in PAYMENT_FAILED / SUBSCRIPTION_PAUSED handlers | billing.py | 380-395 |
| BILL-34 | 🟢 | [ ] | Variant-to-tier mapping duplicated between user and project handlers | billing.py | 309-325, 543-559 |
| BILL-35 | 🟢 | [ ] | Exception message not included in 400 response on malformed JSON webhook | billing.py | 462-467 |
| BILL-36 | 🟢 | [ ] | `lemonsqueezy_variant_id` exists on User model but never stored by user webhook | user.py | 120-122 |
| BILL-37 | 🟢 | [ ] | Sync doesn't clear `personal_project.subscription_expires` when user has no expiry | billing.py | 651-653 |

---

## Section 4: Analytics & Knowledge Vault

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| ANA-22 | 🔴 | [x] | IDOR: `update_conversion_goal` missing `project_id` scope — cross-project modification | analytics.py | 1917-1948 |
| ANA-23 | 🔴 | [x] | IDOR: `delete_conversion_goal` missing `project_id` scope — cross-project deletion | analytics.py | 1951-1972 |
| KV-08 | 🔴 | [x] | Race condition between source ownership check and chunk loading in `query_knowledge` | knowledge.py | 507-521 |
| ANA-24 | 🔴 | [x] | Unbounded `page` parameter (no max bound) on several paginated endpoints | analytics.py | 1599-1610 |
| ANA-25 | 🟠 | [x] | `sort_by` not fully whitelisted — `__class__` or non-column attrs could pass | analytics.py | 1606, 1626 |
| KV-09 | 🟠 | [x] | Knowledge query hard-caps at 500 chunks — 500 × 2KB = 1MB+ loaded into memory | knowledge.py | 543-554 |
| ANA-26 | 🟠 | [x] | Deleting conversion goal doesn't delete associated `ContentConversion` records | analytics.py | 1970 |
| ANA-27 | 🟠 | [x] | `import_conversions` calls `flush()` not `commit()` — data not persisted on interrupt | revenue_attribution.py | 539-546 |
| KV-10 | 🟠 | [x] | Path traversal validation in `reprocess_source` happens AFTER file is read | knowledge.py | 735-756 |
| ANA-28 | 🟠 | [x] | `getattr(ContentDecayAlert, sort_by, ...)` with non-column attrs raises in SQLAlchemy | analytics.py | 1626 |
| ANA-29 | 🟡 | [x] | Decay detection comment notes N+1 issue — verify query is batched correctly | content_decay.py | 95-123 |
| ANA-30 | 🟡 | [x] | Decay dedup is not atomic — two requests can insert duplicate alerts | content_decay.py | 229-251 |
| KV-11 | 🟡 | [x] | `KnowledgeQuery` lacks `project_id` — query stats span all user projects | knowledge.py | 658-676 |
| ANA-31 | 🟡 | [x] | Keyword length not validated in decay detection | content_decay.py | 103-121 |
| ANA-32 | 🟡 | [x] | Article-to-keyword matching is case-sensitive — mismatches if stored in mixed case | content_decay.py | 99, 121 |
| ANA-33 | 🟡 | [x] | `get_aeo_overview` loads ALL AEOScore records — use SQL aggregates instead | aeo_scoring.py | 380-442 |
| ANA-34 | 🟡 | [x] | AI JSON response for decay suggestions has no size limit before parsing | content_decay.py | 313-357 |
| KV-12 | 🟡 | [ ] | No per-source rate limiting on knowledge query endpoint | knowledge.py | 488-517 |
| ANA-35 | 🟢 | [ ] | `GSC_DATA_LAG_DAYS` not communicated to user — users confused by old data | analytics.py | 81-82 |
| ANA-36 | 🟢 | [ ] | `goal_config` accepted without schema validation per `goal_type` | analytics.py | 1877-1948 |
| KV-13 | 🟢 | [ ] | File deletion success not logged — hard to audit file operations | knowledge.py | 468-478 |
| ANA-37 | 🟢 | [ ] | `_normalize_url` has minimal comments — hard to maintain | revenue_attribution.py | 50-68 |
| ANA-38 | 🟢 | [ ] | AEO suggestion JSON parsing uses fragile string manipulation instead of regex | aeo_scoring.py | 349-362 |
| KV-14 | 🟢 | [ ] | File-size error message uses float division — could show unexpected values | knowledge.py | 206-210 |
| ANA-39 | 🟢 | [ ] | `get_content_health_score` recomputes from scratch every call — no caching | content_decay.py | 360-434 |

---

## Section 5: Social Media & Images

### Social Media Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| SM-21 | 🟠 | [x] | SSRF: LinkedIn `post_with_media` downloads from user-supplied URLs without domain whitelist | linkedin_adapter.py | 395-400 |
| SM-22 | 🟠 | [x] | SSRF: Twitter `post_with_media` downloads from user-supplied URLs without domain validation | twitter_adapter.py | 463-468 |
| SM-23 | 🟠 | [x] | SSRF: Facebook `post_with_media` passes user-supplied media URL without local validation | facebook_adapter.py | 459 |
| SM-24 | 🟠 | [x] | SSRF: Instagram `post_with_media` passes user-supplied image URL to Instagram API | instagram_adapter.py | 405, 422 |
| SM-25 | 🟡 | [x] | LinkedIn media download lacks per-file timeout enforcement | linkedin_adapter.py | 397-398 |
| SM-26 | 🟡 | [x] | Twitter media download lacks per-file timeout enforcement | twitter_adapter.py | 465-468 |
| SM-27 | 🟢 | [ ] | Facebook photo upload doesn't validate file size before attempting upload | facebook_adapter.py | 548 |
| SM-28 | 🟡 | [x] | LinkedIn presigned upload URL not validated to be a LinkedIn-controlled domain | linkedin_adapter.py | 541-545 |
| SM-29 | 🔴 | [ ] | Scheduler: single-process mutex missing to prevent concurrent `process_due_posts()` | social_scheduler.py | 67-115 |
| SM-30 | 🟡 | [x] | `retry_after` value from rate limit error not stored — next retry ignores it | social_scheduler.py | 306-330 |
| SM-31 | 🟠 | [ ] | Credential decryption failure doesn't mark account inactive or notify user | social_scheduler.py | 227-235 |
| SM-32 | 🟠 | [ ] | Token refresh failure disables account but never sends email notification (TODO) | social_scheduler.py | 246-261 |
| SM-33 | 🟡 | [x] | `media_urls` not validated as `List[str]` in `CreatePostRequest` schema | social_scheduler.py | 279-285 |
| SM-34 | 🟠 | [x] | OAuth state tokens have no TTL — valid indefinitely, replay attack risk | social.py | 144, 216 |
| SM-35 | 🟡 | [x] | State token returned in JSON body — consider httpOnly cookie for better CSRF protection | social.py | 174-177 |
| SM-36 | 🟡 | [x] | OAuth error redirect passes provider error params without sanitization | social.py | 197-200 |
| SM-37 | 🟡 | [x] | Facebook token exchange doesn't check for `error` field before accessing `access_token` | social.py | 317-320 |
| SM-38 | 🟠 | [x] | New `SocialAccount` created without `project_id` — breaks project isolation | social.py | 271-283 |
| SM-39 | 🟢 | [ ] | Profile picture URLs from Facebook not validated to CDN domain before storage | social.py | 363, 402 |
| SM-40 | 🟡 | [x] | `HTTPException` raised incorrectly in `_facebook_exchange_and_profile` | social.py | 310-315 |
| SM-41 | 🟡 | [x] | `account.platform_user_id` not validated before attempting Facebook/Instagram post | social_scheduler.py | 265-276 |

### Image Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| IMG-21 | 🟡 | [x] | SSRF whitelist bypass: `evil.pbxt.replicate.delivery.com` matches `pbxt.replicate.delivery` | image_storage.py | 405-407 |
| IMG-22 | 🟡 | [x] | Content-type checked AFTER response body read — compromised CDN could return HTML | image_storage.py | 414-419 |
| IMG-23 | 🟢 | [ ] | `int(content_length)` conversion not wrapped in try/except — malformed header crashes | image_storage.py | 421-423 |
| IMG-24 | 🟢 | [ ] | Orphaned file cleanup after failed DB commit has no retry logic | images.py | 129-137 |
| IMG-25 | 🟡 | [x] | `asyncio.wait_for` timeout reached but image record not marked as "failed" | images.py | 94-102 |
| IMG-26 | 🟠 | [x] | `generate_image` validates article_id exists but not that it belongs to current project | images.py | 225-237 |
| IMG-27 | 🟡 | [ ] | `set_featured_image` — image and article validated per-project but not related to each other (by design) | images.py | 458-508 |
| IMG-28 | 🟢 | [ ] | S3 key generation doesn't re-sanitize filename for path traversal | image_storage.py | 262 |
| IMG-29 | 🟠 | [ ] | S3 key extraction from URL is fragile — malformed URL could extract wrong key | image_storage.py | 336-343 |
| IMG-30 | 🟡 | [x] | `delete_image` extracts bucket from URL instead of always using `self.bucket` | image_storage.py | 338 |
| IMG-31 | 🟡 | [x] | CDN domain bypass: if CDN domain is user-controlled, all private images become public | image_storage.py | 371-373 |
| IMG-32 | 🟡 | [x] | `LocalStorageAdapter` — null bytes or repeated slashes could escape `_sanitize_filename` | image_storage.py | 107-109 |
| IMG-33 | 🟢 | [ ] | Image generation semaphore hardcoded to 3 — should be configurable | images.py | 40 |

---

## Section 6: Agency, Admin & Bulk Generation

### Agency Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| AGY-14 | 🟡 | [ ] | Portal timeout can leak workspace existence via timing differences | agency.py | 916-1022 |

### Admin Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| ADM-17 | 🟠 | [x] | `logger.warning()` used in admin_users.py but `logger` never imported/initialized | admin_users.py | 92 |
| ADM-18 | 🟡 | [x] | Race condition: count query and items query are separate — pagination inconsistency | admin_users.py | 199-221 |
| ADM-19 | 🟡 | [x] | `sort_by` passed to `getattr()` without explicit whitelist — AttributeError risk | admin_users.py | 206-209 |
| ADM-20 | 🟢 | [ ] | Audit log truncation relies on exception handling instead of pre-validation | admin_users.py | 86-94 |
| ADM-21 | 🟠 | [x] | Privilege escalation: regular admin can delete images if `project_id is None` | admin_content.py | 544-561 |
| ADM-22 | 🟡 | [x] | Inconsistent permission model across delete_article/outline/image endpoints | admin_content.py | 246-599 |
| ADM-23 | 🟡 | [x] | Missing rate limiting on bulk admin operations (bulk_delete_content, etc.) | admin_content.py | 758-863 |
| ADM-24 | 🟢 | [ ] | N+1: `selectinload(Article.outline)` loaded but never used/returned | admin_content.py | 106 |
| ADM-25 | 🟢 | [ ] | `user_ids` deduplication with `set()` loses order — use `dict.fromkeys()` | admin_content.py | 159, 349 |
| ADM-26 | 🟡 | [x] | User activity count includes suspended users (counts "ever-active" not "currently active") | admin_analytics.py | 129-137 |
| ADM-27 | 🟢 | [ ] | Revenue MRR calculation inferred from user creation date — inaccurate historical data | admin_analytics.py | 731-795 |
| ADM-28 | 🟢 | [ ] | Retention metrics don't filter out DELETED and SUSPENDED users | admin_analytics.py | 364-417 |
| ADM-29 | 🟡 | [x] | Alert list count query uses subquery unnecessarily — inefficient | admin_alerts.py | 76-77 |
| ADM-30 | 🟢 | [ ] | `mark_all_read` could hold lock on large alert tables — needs batch update | admin_alerts.py | 179-198 |

### Bulk Generation Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| BULK-21 | 🔴 | [x] | *(Known)* Bulk outline generation crashes — `generate_outline()` called with extra params | bulk_generation.py | 162-170 |
| BULK-22 | 🟠 | [x] | `update_template` and `delete_template` missing project membership validation | bulk.py | 195-250 |
| BULK-23 | 🟡 | [x] | `KeywordInput` — no minimum content validation (empty/whitespace keywords accepted) | bulk.py | 34-38 |
| BULK-24 | 🟡 | [x] | Project membership check happens AFTER usage limit check in `create_bulk_outline_job` | bulk.py | 342-352 |
| BULK-25 | 🟢 | [ ] | Background task error handling swallows all exceptions in inner try/except | bulk.py | 384-401 |
| BULK-26 | 🔴 | [x] | `generate_outline()` called without `user_id` — billing/usage tracking may fail | bulk_generation.py | 162-170 |
| BULK-27 | 🟠 | [ ] | `ProjectUsageService.check_project_limit()` call — verify signature matches | bulk_generation.py | 133-142 |
| BULK-28 | 🟠 | [x] | `scalar_one_or_none()` used on brand_voice fetch — returns scalar, not project object | bulk_generation.py | 105-110 |
| BULK-29 | 🟡 | [x] | Race condition: job status update to "processing" is not atomic | bulk_generation.py | 87-90 |
| BULK-30 | 🟡 | [x] | Outline language field not set on Outline model instance — only passed to AI | bulk_generation.py | 173-194 |
| BULK-31 | 🟢 | [ ] | Hardcoded 2-second sleep between items — use configurable setting or semaphore | bulk_generation.py | 232 |
| BULK-32 | 🟢 | [ ] | `get_job_with_items` loads all items into memory — no pagination | bulk_generation.py | 265-270 |

### Cross-Cutting Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| CROSS-01 | 🟡 | [ ] | Missing rate limiting on bulk admin operations (DoS vector) | Multiple files | — |
| CROSS-02 | 🟠 | [ ] | Inconsistent audit logging — template CRUD operations not audited | bulk.py, admin_alerts.py | — |
| CROSS-03 | 🟡 | [ ] | Global max-results cap missing — all list endpoints honor page_size ≤ 100 but no total cap | Multiple files | — |

---

## Section 7: Infrastructure & Database

### Database Model Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| DB-01 | 🟠 | [ ] | Migration 032 uses `String(36)` for FK instead of `UUID(as_uuid=False)` — type inconsistency | 032_add_knowledge_project_id.py | 26 |
| DB-02 | 🟠 | [ ] | GSC `access_token` and `refresh_token` stored as plain Text — not encrypted at rest | analytics.py model | 60-61 |
| DB-03 | 🟢 | [ ] | User has both `status=SUSPENDED` and `is_suspended` flag — dual suspension tracking | user.py model | 150-156 |
| DB-04 | 🟡 | [x] | No single-column index on `User.status` — status-only queries are slow | user.py model | 72-76 |
| DB-05 | 🟡 | [ ] | `Project.slug` is globally unique — should be unique per owner (owner_id, slug) | project.py model | 50-51 |
| DB-06 | 🟡 | [x] | No index on `ProjectMember.deleted_at` — soft-delete queries do full table scan | project.py model | — |
| DB-07 | 🟡 | [ ] | GSC OAuth tokens not rotated — stale tokens usable indefinitely if DB is compromised | analytics.py model | 60-64 |
| DB-08 | 🟢 | [ ] | *(Correctly implemented)* `ProjectInvitation.token` unique + indexed | project.py model | 251-256 |
| DB-09 | 🟡 | [x] | `KnowledgeChunk` cascade delete works at DB level but not ORM level — add relationship | knowledge.py model | 138-142 |

### Infrastructure / Security Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| INFRA-AUTH-01 | 🟡 | [x] | JWT decode doesn't validate required fields exist — malformed token passes with None values | tokens.py | 142-149 |
| INFRA-AUTH-05 | 🟡 | [x] | Unverified email (`status=PENDING`) can login if `is_active` is True | auth.py | 242-307 |
| INFRA-01 | 🟠 | [ ] | Password hash column `String(255)` — use `Text` for future-proofing | user.py model | 66 |
| INFRA-02 | 🟡 | [x] | Redis connection pool not configured for rate limiter — each check may create new connection | main.py | 98 |
| INFRA-03 | 🟢 | [ ] | CSP header not yet added — TODO comment exists | main.py | 256 |
| INFRA-06 | 🟡 | [x] | Global exception handler logs raw `str(exc)` — may contain sensitive data (DB strings, paths) | main.py | 196-206 |
| INFRA-11 | 🟢 | [ ] | `/logout` endpoint has no rate limit decorator | auth.py | 584 |
| INFRA-16 | 🟡 | [x] | DB connection doesn't enforce SSL in production | connection.py | 17-23 |
| INFRA-17 | 🟢 | [ ] | `X-Request-ID` not propagated to outbound API calls (Anthropic, email, etc.) | main.py | 235-251 |
| INFRA-18 | 🟢 | [ ] | `get_db_context()` has no timeout — could exhaust connection pool | connection.py | 50-61 |

### Logging & Config Issues

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| LOGGING-01 | 🟢 | [ ] | `JSONFormatter` doesn't handle arbitrary nested extra fields | logging_config.py | 25-27 |
| LOGGING-02 | 🟢 | [ ] | Uvicorn access logs silenced at WARNING level — loses request visibility | logging_config.py | 62 |
| CONFIG-01 | 🟢 | [ ] | Invalid JSON in `CORS_ORIGINS` silently falls back to comma-split — no error raised | settings.py | 82-92 |
| CONFIG-02 | 🟢 | [ ] | `case_sensitive=False` — typo env vars silently ignored, use defaults | settings.py | 25 |
| RATE-LIMIT-01 | 🟡 | [x] | In-memory rate limit fallback silently degrades in multi-worker production | rate_limit.py | 84 |
| RATE-LIMIT-02 | 🟢 | [ ] | `X-Forwarded-For` with private IP (127.0.0.1) not rejected — rate limit bucket spoofing | rate_limit.py | 45-66 |

---

## Section 8: Frontend — Core & Auth

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-AUTH-01 | 🔴 | [x] | Tokens written to localStorage BEFORE Zustand store update — inconsistent state on failure | login/page.tsx | 53-56 |
| FE-AUTH-02 | 🔴 | [x] | Token refresh queue not bounded — if `isRefreshing` not reset, requests stuck forever | api.ts | 108-199 |
| FE-AUTH-03 | 🔴 | [x] | `uploadAvatar` has no file type, size, or MIME validation — arbitrary file upload | api.ts | 352-360 |
| FE-AUTH-04 | 🔴 | [ ] | Auth tokens stored in plain localStorage — XSS steals tokens (architecture issue) | auth.ts | 45, 54, 62 |
| FE-AUTH-05 | 🟠 | [ ] | No CSRF token in request headers — forms vulnerable to cross-site request forgery | api.ts | 58-100 |
| FE-AUTH-06 | 🟠 | [x] | `forceLogout()` uses `window.location.href` — bypasses Zustand cleanup | api.ts | 126-132 |
| FE-AUTH-07 | 🟠 | [ ] | Password change `currentPassword` only requires min(1) — allows single space | password/page.tsx | 15-29 |
| FE-AUTH-08 | 🟠 | [ ] | Raw backend error messages shown to user — leaks internal details | password/page.tsx | 57 |
| FE-AUTH-09 | 🟠 | [ ] | Multiple Enter presses can submit login form multiple times | login/page.tsx | 139-146 |
| FE-AUTH-10 | 🟠 | [ ] | Email field registered in form but disabled — if enabled via DevTools, change is silently dropped | settings/page.tsx | 100-107 |
| FE-AUTH-11 | 🟠 | [ ] | WordPress `app_password` stays in component state until unmount — visible in React DevTools | integrations/page.tsx | 32-36 |
| FE-AUTH-12 | 🟠 | [x] | WordPress `site_url` not scheme-validated — `javascript:` URL accepted | integrations/page.tsx | 237-240 |
| FE-AUTH-13 | 🟠 | [ ] | Billing poll race condition — two setTimeout callbacks can produce duplicate toasts | billing/page.tsx | 69-87 |
| FE-AUTH-14 | 🟡 | [ ] | Network error treated as 401 — user needlessly logged out on connectivity issue | auth.ts | 19-35 |
| FE-AUTH-15 | 🟡 | [ ] | `confirmPassword` validation doesn't enforce same regex as `newPassword` | register/page.tsx | 21-35 |
| FE-AUTH-16 | 🟡 | [ ] | Forgot password success shows full email — email enumeration risk | forgot-password/page.tsx | 64 |
| FE-AUTH-17 | 🟡 | [x] | "Remember Me" checkbox collected in schema but never used in submit handler | login/page.tsx | 21, 123-130 |
| FE-AUTH-18 | 🟡 | [x] | Notification polling fires independently per browser tab — N× API load | layout.tsx | 189-196 |
| FE-AUTH-19 | 🟡 | [ ] | `isLoading` can stay true forever if localStorage cleared mid-load | layout.tsx | 687-717 |
| FE-AUTH-20 | 🟡 | [ ] | No client-side rate limiting on login attempts — full-speed brute force | login/page.tsx | 47-79 |
| FE-AUTH-21 | 🟡 | [ ] | Email verification fires on mount with no user confirmation step | verify-email/page.tsx | 28-39 |
| FE-AUTH-22 | 🟡 | [ ] | Reset password token not validated on mount — user fills form then gets "invalid token" | reset-password/page.tsx | 38-51 |
| FE-AUTH-23 | 🟡 | [ ] | Admin role check `user?.role === "super_admin"` never matches — type only has "admin" | layout.tsx | 343 |
| FE-AUTH-24 | 🟢 | [ ] | WordPress password field missing `autoComplete="off"` | integrations/page.tsx | 257 |
| FE-AUTH-25 | 🟢 | [ ] | Zustand persist serializes full user + token to localStorage JSON | auth.ts | 88-96 |
| FE-AUTH-26 | 🟢 | [ ] | No timeout on email verification — spinner hangs indefinitely on API failure | verify-email/page.tsx | 21-40 |
| FE-AUTH-27 | 🟢 | [ ] | Password schema inconsistent across register / change-password forms | Multiple | — |
| FE-AUTH-28 | 🟢 | [ ] | Notification dropdown stays open after notification click navigates away | layout.tsx | 211-214 |
| FE-AUTH-29 | 🟢 | [ ] | Retry toast doesn't preserve request body — POST retry silently drops data | api.ts | 222-231 |
| FE-AUTH-30 | 🟢 | [ ] | Password/integrations save buttons don't check `isDirty` — wasteful API calls | Multiple | — |

---

## Section 9: Frontend — Content & Generation UI

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-CONTENT-01 | 🟠 | [ ] | Article generation polling race — state update on unmounted component (memory leak) | articles/new/page.tsx | 98-126 |
| FE-CONTENT-02 | 🟡 | [x] | Keyword field accepts blank/whitespace — no client-side validation | articles/page.tsx | 416 |
| FE-CONTENT-03 | 🟡 | [ ] | Outline word count `min={50}` can be bypassed — no max or trim on headings | outlines/[id]/page.tsx | 361-370 |
| FE-CONTENT-04 | 🟡 | [ ] | Auto-save snapshot ref not reset on unmount — stale snapshot after re-open | articles/[id]/page.tsx | 985-1024 |
| FE-CONTENT-05 | 🟠 | [x] | `marked.parse` with `async:false` + DOMPurify — XSS risk if marked allows raw HTML | articles/[id]/page.tsx | 1510-1514 |
| FE-CONTENT-06 | 🟡 | [x] | Bulk job polling fires even when job list is empty | bulk/page.tsx | 74-87 |
| FE-CONTENT-07 | 🟡 | [ ] | Bulk selection state cleared on every keystroke in search — not debounced | articles/page.tsx | 412-418 |
| FE-CONTENT-08 | 🟠 | [ ] | `handleCreate` button — no unique request ID, duplicate job submission possible | bulk/page.tsx | 97-123 |
| FE-CONTENT-09 | 🟡 | [x] | Link suggestions: panel stays open on error with no data and no retry button | articles/[id]/page.tsx | 1112-1127 |
| FE-CONTENT-10 | 🟡 | [ ] | Custom instructions textarea — no warning at 80% char limit, paste can overflow | articles/new/page.tsx | 299-309 |
| FE-CONTENT-11 | 🟢 | [ ] | Icon-only buttons lack `aria-label` — not WCAG compliant | Multiple | — |
| FE-CONTENT-12 | 🟡 | [x] | Bulk delete confirmation wording is grammatically wrong for single item | articles/page.tsx | 224 |
| FE-CONTENT-13 | 🟠 | [ ] | Race condition: auto-save can fire concurrently with revision restore | articles/[id]/page.tsx | 1083-1110 |
| FE-CONTENT-14 | 🟡 | [x] | `restoreRevision` result not null-checked before destructuring | articles/[id]/page.tsx | 1088 |
| FE-CONTENT-15 | 🟡 | [ ] | Inconsistent error message wording across articles/outlines/bulk pages | Multiple | — |
| FE-CONTENT-16 | 🟢 | [ ] | Export dropdown not keyboard-accessible (no Escape/arrow key handling) | articles/[id]/page.tsx | 1286-1307 |
| FE-CONTENT-17 | 🟡 | [x] | AI generation progress component returns null when idle — blank space in UI | ai-generation-progress.tsx | 134 |
| FE-CONTENT-18 | 🟡 | [ ] | Bulk job items list renders all items without pagination — slow at 500+ items | bulk/jobs/[id]/page.tsx | 189-231 |
| FE-CONTENT-19 | 🟡 | [ ] | Word count duplicated in editor and `seo-score.ts` — two implementations diverge | articles/[id]/page.tsx | 65-66 |
| FE-CONTENT-20 | 🟢 | [ ] | Some event listeners may not have cleanup on unmount | articles/[id]/page.tsx | 790-791 |
| FE-CONTENT-21 | 🟡 | [x] | AEO refresh button not disabled during loading — multiple concurrent API calls | articles/[id]/page.tsx | 1169-1181 |
| FE-CONTENT-22 | 🟠 | [x] | Markdown preview uses `dangerouslySetInnerHTML` without CSP — XSS if DOMPurify fails | articles/[id]/page.tsx | 1508-1519 |
| FE-CONTENT-23 | 🟡 | [x] | No error boundary in article editor — one sub-component crash kills entire page | articles/[id]/page.tsx | 1-699 |
| FE-CONTENT-24 | 🟡 | [x] | Bulk keyword input doesn't deduplicate — duplicate keywords waste quota | bulk/page.tsx | 89-95 |
| FE-CONTENT-25 | 🟢 | [ ] | Modal/dropdown focus not moved in or restored on close — not accessible | Multiple | — |
| FE-CONTENT-26 | 🟡 | [ ] | Retry toast may not preserve POST request config properly | api.ts | 211-235 |
| FE-CONTENT-27 | 🟡 | [ ] | Manual article creation shows generic field error, no per-field highlighting | articles/new/page.tsx | 133-137 |
| FE-CONTENT-28 | 🟠 | [ ] | `setInterval` polling not guaranteed to clear on unmount — memory leak | articles/new/page.tsx | 95-126 |
| FE-CONTENT-29 | 🟡 | [x] | Article slug passed to SerpPreview without validation — undefined breaks preview | articles/[id]/page.tsx | 1569 |
| FE-CONTENT-30 | 🟢 | [ ] | Pagination and filter state not persisted in URL — lost on navigation | articles/page.tsx | 69-76 |

---

## Section 10: Frontend — Analytics, Social, Images & Admin UI

### Analytics

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-ANA-01 | 🟡 | [x] | Analytics page status check errors only logged to console — no user feedback | analytics/page.tsx | 74-85 |
| FE-ANA-02 | 🟡 | [x] | Device/country breakdowns don't use same `dateRange` as summary/daily data | analytics/page.tsx | 141-142 |
| FE-ANA-03 | 🟢 | [ ] | CSV export doesn't escape commas in keyword names — breaks CSV parsing | keywords/page.tsx | 145-147 |
| FE-ANA-04 | 🟢 | [ ] | Page URL rendered in `href` without XSS validation | pages/page.tsx | 375-384 |
| FE-ANA-05 | 🟠 | [x] | `handleDetect/Suggest/Resolve` lack debounce — button mashing fires multiple requests | content-health/page.tsx | 130-177 |
| FE-ANA-06 | 🟡 | [ ] | `overview.score_distribution` not null-checked — `Object.entries()` throws if missing | aeo/page.tsx | 185 |
| FE-ANA-07 | 🟢 | [ ] | Pagination not reset when date range changes — user can be on stale page | articles/page.tsx | 52-56 |
| FE-ANA-08 | 🟡 | [ ] | Analytics callback page doesn't validate CSRF state before `handleCallback` | callback/page.tsx | 33-41 |
| FE-ANA-09 | 🟢 | [ ] | Max keyword selection limit reached — no disabled state with tooltip, just error toast | opportunities/page.tsx | 130-134 |
| FE-ANA-10 | 🟡 | [x] | `goal_config` arbitrary JSON submitted without schema validation | revenue/page.tsx | 153-173 |

### Social Media

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-SM-01 | 🟡 | [x] | Upload fail doesn't clearly warn user images weren't sent | social/compose/page.tsx | 139-150 |
| FE-SM-02 | 🟠 | [ ] | Draft restoration references stale account IDs — validation error on deleted accounts | social/compose/page.tsx | 95-112 |
| FE-SM-03 | 🟢 | [ ] | Callback page could fire twice if user refreshes during redirect | social/callback/page.tsx | 40-46 |
| FE-SM-04 | 🟠 | [ ] | Post history filters applied client-side — only first 20 posts are filterable | social/history/page.tsx | 34-53 |
| FE-SM-05 | 🟢 | [ ] | Calendar requests 1000 posts regardless of period — could timeout | social/calendar/page.tsx | 53 |
| FE-SM-06 | 🟡 | [x] | Post detail page doesn't validate `postId` before API call | social/posts/[id]/page.tsx | 42, 54-70 |
| FE-SM-07 | 🟢 | [ ] | No check for duplicate account before redirect to connect | social/accounts/page.tsx | 45-56 |

### Images

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-IMAGES-01 | 🟠 | [x] | Image generation polling stops after 90 attempts with no user notification | images/generate/page.tsx | 146-177 |
| FE-IMAGES-02 | 🟡 | [x] | Bulk image delete doesn't validate selected IDs still exist | images/page.tsx | 261-273 |
| FE-IMAGES-03 | 🟢 | [ ] | Client-side filtering bypasses pagination — all matches shown without paging | images/page.tsx | 129-152 |
| FE-IMAGES-04 | 🟢 | [ ] | No loading state on copy/download/send image operations | images/page.tsx | 523-569 |

### Knowledge

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-KNOWLEDGE-01 | 🟡 | [ ] | Query history stored in localStorage without size limit — quota exceeded risk | knowledge/query/page.tsx | 55-62 |
| FE-KNOWLEDGE-02 | 🟢 | [ ] | Sources page Refresh button not disabled during loading | knowledge/sources/page.tsx | 71-74 |
| FE-KNOWLEDGE-03 | 🟡 | [ ] | Markdown rendering of query responses not sanitized — XSS from malicious KB content | knowledge/query/page.tsx | 156-202 |

### Admin

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-ADMIN-01 | 🟠 | [x] | Admin dashboard LineChart tries to format dates but gets strings — may fail | admin/page.tsx | 206-209 |
| FE-ADMIN-02 | 🟢 | [ ] | Stats API null/undefined fields crash PieChart rendering | admin/page.tsx | 74-81 |

### Portal

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-PORTAL-01 | 🟢 | [ ] | `brand_colors` hex not validated before use in CSS — invalid value breaks styling | portal/[token]/page.tsx | 133-137 |
| FE-PORTAL-02 | 🟡 | [x] | Portal data fetch has no timeout — spinner hangs indefinitely | portal/[token]/page.tsx | 108-125 |
| FE-PORTAL-03 | 🟢 | [ ] | `footer_text` rendered as raw HTML — XSS if agency inputs malicious HTML | portal/[token]/page.tsx | 387-388 |

### Cross-Cutting Frontend

| ID | Sev | Status | Description | File | Line |
|----|-----|--------|-------------|------|------|
| FE-MISC-01 | 🟡 | [ ] | Inconsistent error handling — some use toast, some only set state | Multiple | — |
| FE-MISC-02 | 🟢 | [ ] | Skeleton loaders don't match content dimensions — causes CLS | Multiple | — |
| FE-MISC-03 | 🟠 | [x] | No global error boundary for unhandled Promise rejections — page breaks silently | All pages | — |
| FE-MISC-04 | 🟡 | [x] | CSV export uses fragile `document.createElement` approach | keywords, pages | 150-157 |
| FE-MISC-05 | 🟢 | [ ] | Date/time formatting inconsistent — `toLocaleDateString`, `date-fns`, custom all mixed | Multiple | — |
| FE-MISC-06 | 🟡 | [x] | `useParams()` results not type-guarded — array instead of string causes TypeError | Multiple | — |
| FE-MISC-07 | 🟢 | [ ] | Missing helpful empty states in some pages (table shows blank instead of CTA) | Multiple | — |

---

## Priority Fix Order

### Immediate (Critical — fix before next deploy)
1. **PROJ-25** — Schema role "member" vs "editor" mismatch — invitation inserts fail
2. **GEN-21** — `AIGenerationError` undefined — NameError crashes generation
3. **GEN-28** — Usage limit check + increment not atomic — quota bypass
4. **BULK-21 / BULK-26** — Bulk outline generation crashes (known issue)
5. **ANA-22 / ANA-23** — IDOR in conversion goal update/delete
6. **BILL-17** — Checkout URL injection via unencoded email parameter
7. **FE-AUTH-01** — Double token storage — inconsistent auth state
8. **FE-AUTH-02** — Refresh queue can lock permanently
9. **FE-AUTH-03** — No file type/size validation on avatar upload

### Next Sprint (High)
- SM-21 through SM-24 (SSRF in social media adapters)
- SM-34 (OAuth state tokens never expire)
- SM-38 (SocialAccount created without project_id)
- IMG-26 (image generation without project_id validation)
- IMG-29 (fragile S3 key extraction)
- ADM-17 (undefined logger in admin_users.py)
- ADM-21 (privilege escalation via orphaned images)
- BULK-22 / BULK-27 / BULK-28 (bulk service issues)
- BILL-18 / BILL-19 / BILL-20 / BILL-21 / BILL-22 (webhook race conditions + validation)
- DB-02 (GSC tokens not encrypted)
- CROSS-02 (missing audit logs for template ops)
- FE-AUTH-05 through FE-AUTH-13 (CSRF, logout, WordPress, billing poll)
- FE-CONTENT-05 / FE-CONTENT-22 (XSS in markdown preview)
- FE-CONTENT-13 / FE-CONTENT-28 (race conditions in revision restore and polling)
