# AdCreative.ai product and architecture research

Research date: 2026-07-29

## Executive conclusion

AdCreative.ai is not one feature. It is a multi-tenant creative operations platform with four product layers:

1. A brand-aware workspace for users, teams, projects, assets, billing, and integrations.
2. A deterministic design and rendering system for turning structured brand/content inputs into many ad layouts and sizes.
3. Several AI pipelines for text, images, product photography, fashion, video, compliance, personas, and scoring.
4. A data platform that imports ad-account performance and competitor data, then turns it into insights and predictions.

A convincing first product does not require matching every AI feature. The strongest first vertical slice is:

`website/brand onboarding -> ad brief -> copy and image suggestions -> deterministic template rendering -> editable variants -> download and credit charge`

The scoring and insights claims are the hardest parts to reproduce honestly. A useful heuristic score can be built early, but a calibrated performance predictor requires a large dataset linking actual creatives to impressions, clicks, conversions, spend, audience, placement, and time.

This should be developed as a functionally similar, clean-room product with its own name, interface, templates, assets, and implementation. AdCreative.ai's current terms explicitly restrict reverse engineering, recreation, derivative works, and competitive use of its service. Its trademarks, exact visual design, copy, templates, assets, and proprietary models must not be copied.

## Evidence levels

- **Verified** means visible on an official AdCreative.ai page, help article, API document, legal page, or publicly served application asset.
- **Observed** means derived from the public application HTML, headers, or production JavaScript delivered to unauthenticated visitors.
- **Inferred** means an architectural conclusion that fits the evidence but is not confirmed by AdCreative.ai.
- **Recommended** describes how our own implementation should work, not how AdCreative.ai necessarily works internally.

## 1. Current product surface

### 1.1 Generate

The current public navigation exposes:

- Ad creatives in platform-specific sizes.
- Instant Ads from a website or product URL.
- Ad copy and headline generation.
- AI image and AI stock-video generation.
- Product photoshoots and product videoshoots.
- Fashion photoshoots/virtual try-on and fashion videoshoots.
- UGC-style videos.
- A creative utility suite: background removal, upscaling, face enhancement, and text-to-speech.
- Buyer personas.
- Storytelling and other video-generation modes are also visible in the current product surface.

The central workflow is brand-first. A user creates a brand by scanning a website or entering a name, description, logo, and colors. Projects then reuse the brand context. Generated outputs can be selected, edited, downloaded, saved to a library, or pushed into an ad platform's media library.

Official workflow evidence:

- [Product overview](https://www.adcreative.ai/)
- [Brand setup](https://help.adcreative.ai/en/articles/5713533-how-to-add-a-brand)
- [Project creation](https://help.adcreative.ai/en/articles/5713794-how-to-create-a-new-project)
- [Instant Ads](https://www.adcreative.ai/instant-ads)
- [Product photoshoot workflow](https://help.adcreative.ai/en/articles/9760152-how-to-use-the-product-photo-ads)
- [Fashion videoshoots](https://www.adcreative.ai/fashion-videoshoot)
- [Creative utility suite](https://www.adcreative.ai/creative-utility-suite)

### 1.2 Analyze and predict

- Creative Insights imports a brand's ad-account history and surfaces best creatives/copy, benchmarks, and fatigue signals.
- Creative Optimization/Tracking views campaign and creative state over time.
- Competitor Insights accepts a competitor URL and reports estimated traffic, demographics, channels, pages, and notable ads.
- Creative Scoring predicts performance/awareness and recommends design changes.
- Compliance Checker reviews creative content against brand, platform, and regional/legal rules.
- Buyer Personas turns website context into audience profiles and suggested tactics.
- An inspiration gallery stores or discovers ad references.

The company's “over 90% accuracy”, “up to 14x”, and training-data-volume statements are marketing claims, not independently verified measurements. They should not be repeated as guarantees in our product.

Sources:

- [Creative Insights workflow](https://help.adcreative.ai/en/articles/5713470-how-can-i-connect-my-ad-accounts)
- [Competitor Insights](https://www.adcreative.ai/competitor-insights-ai)
- [Custom templates and real-time scoring](https://www.adcreative.ai/custom-templates)
- [Enterprise and data-governance claims](https://www.adcreative.ai/enterprise)

### 1.3 Automate, edit, and collaborate

The product supports:

- Custom layered templates.
- Dynamic text, logos, buttons, images/backgrounds, prices, and discounts.
- Batch generation using direct-match or cross-match combinations.
- Multi-size output and localization.
- Layers, frames, safe zones, comments, folders, duplication, and previews.
- Team invitations, multiple users, brands, and managed accounts.
- A reusable asset library with favorites, folders, recent downloads, and bulk actions.
- White-labeling and enterprise-specific fine-tuning surfaces.

### 1.4 Monetization

The self-service product uses subscriptions with limits on brands and users. “Unlimited generation” is paired with credits that are generally consumed when a user downloads an output; some specialized generation actions can also have their own credit cost. The production application checks credit sufficiency before downloads and supports add-on credits.

The exact displayed prices and included limits change with billing period and promotions. Our implementation should model plans, entitlements, and a credit ledger separately rather than hard-coding pricing into UI logic.

Source: [public pricing and credit explanation](https://www.adcreative.ai/pricing)

## 2. Frontend research

### 2.1 Public marketing frontend

**Observed**

- The public site is built with Webflow assets and served behind Cloudflare.
- It is a multilingual content/SEO site separate from the authenticated application.
- It contains a large feature-navigation system, product demos, pricing widgets, case studies, forms, and campaign-specific variants.

**Recommended**

Keep the marketing site and product application independently deployable. They have different release cadence, caching, SEO, security headers, and ownership.

### 2.2 Authenticated application frontend

**Observed from the public production app**

- React 18.2 single-page application.
- Vite-generated production bundles and lazy-loaded feature chunks.
- REST-oriented request layer.
- SignalR event subscriptions for render request, completion, and error updates.
- Fabric.js is included for canvas-style design functionality.
- Internationalization, light/dark themes, and white-label theme settings.
- Sentry error reporting.
- Chargebee components plus Stripe-backed payment presentation.
- Google and Microsoft login in addition to email/password.
- OIDC authorization-code flow with PKCE and `openid profile` scopes.
- Responsive/mobile-specific controls and a PWA manifest.
- Intercom/help, product-update, push, experimentation, and analytics integrations.

Public entry point: [AdCreative.ai application](https://app.adcreative.ai/)

### 2.3 Main application routes and screens

A functionally comparable frontend needs these areas:

| Area | Main screens and responsibilities |
| --- | --- |
| Authentication | Register, login, social login, callback, logout, verification, password recovery, optional 2FA |
| Workspace | Brand switcher, plan/credit state, notifications, help, global navigation |
| Brands | Brand list, create/edit, website scan review, logo/colors/fonts, brand identity, connected accounts |
| Projects | Project list/filter/search, new project, saved draft, generated results, favorites and bulk selection |
| Generation wizard | Feature selector, output sizes, brief/copy, asset picker, styles/templates, review and generate |
| Results | Live job progress, variant grid, score badges, favorite, edit, resize, regenerate, save, download/push |
| Creative editor | Artboard, layers, text/image/logo/button controls, alignment, colors, fonts, undo/redo, autosave |
| Template builder | Frames/sizes, dynamic fields, safe zones, preview data, comments, versions, batch rendering |
| Library | Uploads, AI outputs, downloads, folders, search, filters, metadata and bulk actions |
| Insights | KPI cards, time filters, charts, creative table/grid, fatigue alerts, shared dashboards |
| Scoring/compliance | Upload or select asset, analysis progress, score breakdown, recommendations, report |
| Integrations | OAuth connections, ad-account selection, per-brand mapping, sync status, revoke/reconnect |
| Team/settings | Members, invitations, profile, language/theme, security, notifications, billing and invoices |

### 2.4 Frontend state boundaries

Recommended state split:

- Server state: query cache for brands, projects, assets, jobs, integrations, and reports.
- Local workflow state: generation wizard draft and validation.
- Editor state: normalized scene graph plus undo/redo command history.
- Session state: user, workspace, entitlements, credits, flags, theme, and locale.
- Realtime state: job progress events merged idempotently into server state.

The editor document must be serializable and versioned. The UI should never treat a rendered PNG as the source of truth; the source of truth is a scene graph containing artboard, layers, constraints, fonts, asset references, and dynamic bindings.

### 2.5 Frontend-specific risks

- A reliable editor is a product in itself: selection math, text measurement, font loading, snapping, cropping, and undo/redo create substantial complexity.
- Browser rendering and server rendering can diverge because of fonts and text layout.
- Hundreds of variants require virtualization, thumbnails, lazy loading, and careful memory management.
- Long AI jobs require resumable UI state. Refreshing or reopening a project must reconnect to the job rather than restart it.
- Uploads need progress, cancellation, retry, client-side previews, and strict server validation.

## 3. Verified backend behavior

### 3.1 Main SaaS backend

**Observed**

- The login surface and standard error shapes strongly indicate an ASP.NET Core identity/backend stack.
- Authentication is OIDC with authorization code and PKCE.
- The SPA talks to same-origin REST-style resources for users, brands, projects, renders, subscriptions, integrations, assets, insights, templates, and specialized AI features.
- SignalR is used to deliver render progress/completion/errors to the application.
- Billing surfaces use Chargebee and Stripe-related flows.
- The application has domain concepts absent from the external generation API: brands, projects, packages, subscriptions, credits, teams, library, and integrations.

The internal language and database cannot be proven from public behavior alone. ASP.NET Core is a strong inference, while the exact database is unknown.

### 3.2 Separate public generation API

AdCreative.ai's own documentation explicitly says its generation API:

- Runs independently of the main product.
- Has its own services, database, codebase, and operational logic.
- Is stateless and domain-agnostic.
- Knows `ApplicationId` and an optional integrator-supplied `UserId`.
- Does not natively know UI concepts such as Brand, Project, Customer, or Package.
- Returns a render-process identifier that the caller maps to its own domain.

Its common generation lifecycle is:

1. Generate/refresh JWT credentials.
2. Start a feature-specific generation request.
3. Receive a render-process ID and task IDs.
4. Poll progress or consume webhook/RabbitMQ notifications.
5. Download the final output.

Supported documented APIs include ad-creative rendering/editing, product photoshoots, stock images, background removal, upscaling, face enhancement, website scanning, and ad-text generation. The public docs mark scoring/fine-tuning API sections as future work.

Sources:

- [API core capabilities](https://api-docs.adcreative.ai/docs/getting-started/quickstart/core-capabilities)
- [Authentication](https://api-docs.adcreative.ai/docs/getting-started/authentication)
- [AdCreative rendering API](https://api-docs.adcreative.ai/docs/features/adcreative-api)
- [Notification model](https://api-docs.adcreative.ai/docs/getting-started/notifications)

### 3.3 Generation and notification behavior

The public API models a generation as a process with one or more tasks. States include not started, started, scheduled, cancelled, failed, and succeeded. Clients can poll per user/application or configure webhooks/RabbitMQ.

The webhook model includes per-task completion and aggregate progress events. The current documentation warns that webhook endpoint authentication is not yet supported. Our implementation should improve this with HMAC signatures, timestamp/replay checks, idempotency keys, delivery logs, and a dead-letter/retry policy.

Source: [receiving notifications](https://api-docs.adcreative.ai/docs/getting-started/notifications/how-to-receive-notifications)

### 3.4 Verified AI pipeline details

- Website scan extracts brand name/type/description, logo URLs or SVG, main colors, and palettes.
- Ad text generation accepts product, description, audience, framework/type, tone, language, website, CTA, emoji preference, and custom instructions. It returns variants with predicted conversion scores.
- Product Photoshoot performs background removal/tagging, recommends prompts/presets, and generates up to six scene variations.
- The Product Photoshoot API documentation explicitly identifies a fine-tuned Stable Diffusion inpainting model optimized for product placement.
- Utility APIs follow the same start -> progress -> download pattern.

Sources:

- [Website scanner API](https://api-docs.adcreative.ai/docs/features/scan-my-website-api)
- [Ad text API](https://api-docs.adcreative.ai/docs/features/ad-text-generation-api)
- [Product Photoshoot API](https://api-docs.adcreative.ai/docs/features/product-photoshoot-api)
- [Image Upscaler API](https://api-docs.adcreative.ai/docs/features/image-upscaler-api)
- [Background Remover API](https://api-docs.adcreative.ai/docs/features/background-remover-api)

## 4. Backend services required for a comparable product

These are recommended bounded contexts. They do not all need to be separate deployments on day one.

| Context | Responsibilities |
| --- | --- |
| Identity and access | OIDC/social login, sessions, verification, recovery, 2FA, roles, service tokens |
| Tenant/team | Workspaces, members, invitations, managed accounts, audit history |
| Entitlements/billing | Plans, limits, trials, subscriptions, invoices, metered actions, atomic credit ledger |
| Brand intelligence | Website crawl, metadata extraction, logos, colors, fonts, product/audience summaries |
| Project/draft | Project lifecycle, wizard drafts, input snapshots, favorites, revisions |
| Asset/library | Upload sessions, MIME/size validation, malware scan, EXIF handling, folders, CDN metadata |
| Template/editor | Scene graphs, template versions, dynamic fields, constraints, comments, safe zones |
| Render | Deterministic SVG/raster/video composition, resizing, font handling, previews, exports |
| Generation orchestrator | Idempotent jobs, task fan-out, queueing, retries, cancellation, progress aggregation |
| AI inference gateway | Provider/model routing, prompt versions, safety, cost/latency tracking, fallback |
| Text intelligence | Product description, strategies, copy, translation, shortening, tone/variation |
| Image intelligence | Generation, segmentation, in/outpainting, background removal, upscale, face/detail enhancement |
| Video intelligence | Image-to-video, templates, voice/audio, captions, avatar/UGC orchestration, FFmpeg assembly |
| Scoring/compliance | Feature extraction, prediction, rule/RAG analysis, explanation and report generation |
| Ad integrations | OAuth tokens, accounts, scheduled sync, normalized metrics, media-library push |
| Insights/competitors | ETL, aggregates, benchmarks, fatigue, competitor snapshots and reports |
| Notifications | Realtime events, webhooks, email, push, retry/dead-letter handling |
| Admin/observability | Feature flags, model/prompt releases, support tools, traces, metrics, cost and moderation |

## 5. Recommended high-level architecture

```text
Marketing site                 Product web app
      |                               |
   CDN/WAF                  API gateway / BFF + OIDC
                                      |
            +-------------------------+-------------------------+
            |                         |                         |
      SaaS domain app          Generation orchestrator    Integration/ETL
  users/brands/projects/       jobs/tasks/progress        ad accounts/data
  billing/library/templates          |                         |
            |                    durable queue             scheduler/queue
       PostgreSQL               /          \                    |
            |             CPU renderers   GPU/AI workers   analytics store
            |                  |              |
            +------------- object storage / CDN ----------------+
                                      |
                         SignalR/SSE + signed webhooks
```

### Start simpler than this diagram

Use a modular monolith for the SaaS domain and one worker service for asynchronous jobs. Keep boundaries explicit in code and data, but do not deploy a large microservice fleet before traffic, security isolation, or independent scaling requires it.

Separate GPU inference and rendering workers early because they have different dependencies, hardware, scaling, timeout, and failure characteristics from the transactional web application.

## 6. Core data model

Suggested primary entities:

- `User`, `Workspace`, `Membership`, `Invitation`, `Role`
- `Plan`, `Subscription`, `Entitlement`, `CreditWallet`, `CreditTransaction`
- `Brand`, `BrandIdentityVersion`, `BrandAsset`
- `IntegrationConnection`, `AdAccount`, `BrandAdAccountMap`, `SyncCursor`
- `Project`, `ProjectDraft`, `GenerationRequest`, `GenerationTask`
- `Asset`, `AssetVariant`, `Folder`, `AssetUsage`
- `CreativeDocument`, `DocumentVersion`, `Layer`, `Template`, `TemplateVersion`
- `RenderOutput`, `Download`, `PushOperation`
- `CreativeScore`, `ScoreModelVersion`, `ComplianceReport`
- `InsightSnapshot`, `CampaignMetric`, `CreativeMetric`, `CompetitorSnapshot`
- `BuyerPersona`, `PromptVersion`, `ModelRun`
- `WebhookEndpoint`, `WebhookDelivery`, `Notification`
- `AuditEvent`

Important rules:

- Every tenant-owned row carries `workspace_id`.
- Every AI result records model/provider/version, prompt-template version, seed/settings, input asset hashes, safety result, latency, and cost.
- Credit charging uses a double-entry or append-only ledger and an idempotency key.
- Assets are immutable; edits create new versions/variants.
- Generated files use object storage. The relational database stores metadata and references, not large binaries.
- OAuth refresh tokens and provider secrets are encrypted with envelope encryption and never returned to the browser.

## 7. Feature pipelines

### 7.1 Website-to-ad

1. Fetch with strict SSRF protection.
2. Render JavaScript only when necessary.
3. Extract metadata, product/offer text, images, logo candidates, fonts, and colors.
4. Rank/deduplicate assets.
5. Produce a structured brand/product brief with an LLM.
6. Generate copy angles and platform-length variants.
7. Retrieve or generate visual candidates.
8. Bind content to original templates.
9. Render all requested sizes.
10. Run safety/compliance checks and return editable variants.

### 7.2 Deterministic ad rendering

The layout engine, not image generation, is the core of dependable ad output. Use templates with constraints:

- Artboard and safe zones.
- Text boxes with min/max font size, wrapping, truncation, and fit strategy.
- Image crop/focal point and masks.
- Logo clearance and contrast.
- CTA sizing and placement.
- Conditional layers and variants.
- Bindings such as headline, price, discount, product image, logo, and background.

Render the same scene graph in preview and export. Server-side SVG composition plus a headless rasterizer is a practical starting point. Use FFmpeg for video assembly.

### 7.3 Product photos

1. Validate and normalize input.
2. Segment the product and estimate product category/caption.
3. Let the user choose preset or custom scenes.
4. Generate/inpaint the environment while preserving the product pixels where possible.
5. Match contact shadow, lighting, color, and perspective.
6. Run artifact detection and optionally upscale.
7. Offer “convert to ad” by passing the result into the template renderer.

### 7.4 Scoring

An honest roadmap:

- Phase 1: explainable design checks and heuristics, labeled as recommendations rather than performance probability.
- Phase 2: learn within each connected customer account from normalized historical metrics.
- Phase 3: train a cross-customer model only with appropriate consent, anonymization, leakage controls, placement/category normalization, and calibrated offline/online evaluation.

CTR alone is a biased label. Training data must account for audience, bid, budget, objective, placement, geography, seasonality, frequency, and campaign age. Otherwise the model will attribute campaign effects to the creative.

### 7.5 Compliance

Use a hybrid system:

- Versioned deterministic rules for size, text length, prohibited elements, and brand constraints.
- OCR and visual classifiers.
- Retrieval over current platform policies by country/platform/category.
- A multimodal model for explanations and ambiguous cases.
- Human-review/escalation state for high-risk categories.

Never market this as legal approval. Policies change and the system can make mistakes.

## 8. Infrastructure, security, and compliance

AdCreative.ai states that self-service data is stored on AWS in Ireland, uses HTTPS, supports 2FA for sensitive actions, follows GDPR, retains most disabled-account personal data for 180 days, and may use anonymized data for AI training. Its enterprise page advertises selectable data regions and dedicated/fine-tuned deployments.

Sources:

- [Privacy policy](https://www.adcreative.ai/privacy-policy)
- [Enterprise data governance](https://www.adcreative.ai/enterprise)

Our minimum controls:

- CDN/WAF, rate limits, bot/abuse controls, and signed upload URLs.
- SSRF-safe crawler with DNS/IP revalidation and blocked private/link-local/metadata ranges.
- Strict tenant authorization at both service and query layers.
- Encryption in transit and at rest; managed key service for secrets/tokens.
- Upload type/size/dimension limits, decompression-bomb protection, malware scan, EXIF removal.
- Content moderation before and after generation.
- Immutable audit log for billing, downloads, integration changes, and admin actions.
- Data deletion/export workflows and explicit AI-training consent.
- Regional storage policy and processor inventory.
- Backups with restore testing, queues with dead letters, and job idempotency.
- Per-model cost ceilings, timeouts, and circuit breakers.
- HMAC-signed webhooks and replay protection.

No official source found in this research confirms SOC 2 or ISO 27001 certification, so those claims should not be assumed.

## 9. External dependencies

A practical implementation will likely buy before building:

- Identity/social login.
- Subscription billing and tax handling.
- Transactional email.
- Object storage/CDN.
- Error monitoring and product analytics.
- One or more LLM/image/video providers for initial inference.
- Background removal/upscaling if self-hosting is not initially economical.
- Stock-photo licensing/search.
- Ad-platform APIs.

Ad platform integrations require separate developer applications, reviews, scopes, token handling, and ongoing API-version maintenance. AdCreative.ai's help center currently names Meta, Google, LinkedIn, and Pinterest for self-service connections. Pushing an image sends it to the platform media library; it does not automatically publish a live campaign.

Sources:

- [Supported account connections](https://help.adcreative.ai/en/articles/5730072-how-many-ad-accounts-can-i-add-to-my-account)
- [Push behavior](https://help.adcreative.ai/en/articles/8794326-how-to-push-creatives-to-your-ad-account)

## 10. Scope recommendation for the implementation discussion

### Credible MVP

- Auth, workspace, one user role.
- Brand creation by URL plus manual correction.
- Project wizard for static ads.
- LLM copy generation and translation.
- User upload plus generated/stock image selection.
- 15-30 original responsive templates across 3-4 sizes.
- Server-side rendering, result gallery, small editor, download.
- Subscription, credit ledger, asset library, job progress.
- Basic moderation, audit, observability, and deletion/export.

### Product-market-fit expansion

- Teams, invitations, comments, template builder, batch/localization.
- Product photoshoots and utility tools.
- Meta/Google account connections and media push.
- Customer-specific creative insights.
- Rule-based scoring and compliance.

### Full-platform expansion

- Video/UGC/fashion pipelines.
- Cross-account scoring models and calibrated benchmarks.
- Competitor intelligence and large-scale ad ingestion.
- Enterprise fine-tuning, white label, data residency, DAM API, approvals.

## 11. Decisions to make before implementation

1. Who is the first buyer: small business, ecommerce brand, or agency?
2. Is the first deliverable static ads only, or must it include video?
3. Do we optimize for fast provider-backed launch or self-hosted/open-model inference?
4. Which ad platforms are required in the first release?
5. Is the editor a lightweight text/image adjustment tool or a Canva-like editor?
6. What actions consume credits: generation, high-resolution render, download, or all three?
7. What privacy promise will we make about customer assets and model training?
8. Which region and expected concurrency/GPU budget should drive deployment?
9. Will scoring initially be an explainable heuristic, or is real campaign data already available?
10. What original product name and visual identity will replace AdCreative.ai branding?

## 12. Research limitations

- No authenticated account was used, so post-login behavior was reconstructed from official help material, public production assets, and API documentation.
- The private infrastructure, databases, models beyond publicly documented details, training pipeline, and vendor contracts are not observable.
- Public API documentation was last materially updated in 2024-2025 and does not cover every feature visible in the July 2026 application.
- Marketing performance claims were not independently validated.
- Exact pricing is intentionally not treated as stable because the public site shows billing-period and campaign-dependent offers.

## Primary source index

- [Official product site](https://www.adcreative.ai/)
- [Official help center](https://help.adcreative.ai/en/)
- [Official API documentation](https://api-docs.adcreative.ai/docs)
- [API core capabilities](https://api-docs.adcreative.ai/docs/getting-started/quickstart/core-capabilities)
- [Current online-subscriber terms](https://www.adcreative.ai/legal/en/terms-of-service-for-online-subscribers)
- [Privacy policy](https://www.adcreative.ai/privacy-policy)
