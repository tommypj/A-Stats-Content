# A-Stats Engine - Master TODO

> **Status Legend:** [ ] Pending | [~] In Progress | [x] Complete | [!] Blocked

---

## Phase 0: Scaffolding & Setup
- [x] Initialize workspace with `uv`
- [x] Install core dependencies (FastAPI, SQLAlchemy, pgvector, Anthropic)
- [x] Build /backend directory structure (Clean Architecture)
- [x] Implement `dev_overseer.py` for Telegram oversight
- [x] Configure database migrations (Alembic)
- [x] Set up testing framework (pytest)
- [ ] Configure CI/CD pipeline

---

## 1. Onboarding & Setup (11 functions) ✅
- [x] Register Account - Create new account with email/password
- [x] Sign In - Log in with email/password credentials
- [x] Google OAuth Login - Sign in with Google account
- [x] Verify Email Address - Confirm email via verification link
- [x] Resend Verification Email - Request new verification link
- [x] Connect Google Search Console - Authorize GSC access for keyword data
- [x] View GSC Properties - See all connected Search Console properties
- [x] Select Primary Website - Choose which GSC property to track
- [x] Connect WordPress - Link WordPress site for auto-publishing
- [x] Skip WordPress Setup - Skip WP connection to configure later
- [x] Check Setup Status - See onboarding completion progress

---

## 2. Dashboard (8 functions) ✅
- [x] View Dashboard Overview - See content stats and recent activity
- [x] View Summary Stats - Total outlines, drafts, pending, published counts
- [x] Launch Manual Strategy - Create outline for any keyword with optional brief
- [x] View GSC Opportunities - See top keyword opportunities from Search Console
- [x] Apply GSC Filters - Filter by impressions, position, date range
- [x] Create Outline from Opportunity - Generate outline from GSC keyword
- [x] View Recent Outlines - See last 5 outline cards with status
- [x] Access Quick Links - Navigate to Analytics, Settings, Content Lab

---

## 3. Content Generation (9 functions) ✅
- [x] Create Content Outline - Create new outline with keyword data
- [x] Generate Full Article - Expand outline into complete article (sync)
- [x] Generate Async Content - Non-blocking generation with job tracking
- [x] Check Generation Status - Poll progress of async generation
- [x] Monitor Progress - Real-time progress updates via streaming
- [x] Set Content Language - Configure language for generated content
- [x] Define Content Persona - Select writing persona for tone/voice
- [x] Add Custom Brief - Provide AI direction/guidelines
- [x] Track Credit Usage - See credits consumed per action

---

## 4. Content Management (12 functions) ✅
- [x] View All Outlines - Browse content library with filters
- [x] Filter by Status - Show Draft, Pending Review, Approved, Published
- [x] View Imported Archive - See WordPress posts imported for tracking
- [x] Switch Production/Archive - Toggle between created and imported content
- [x] Edit Outline Details - Modify title, keyword, metadata
- [x] Edit Article Content - Edit generated article via markdown editor
- [x] View Article Preview - See rendered HTML preview
- [x] Delete Outline - Remove outline and associated content
- [x] Download Content Packet - Export outline with all metadata as ZIP
- [x] Export to WordPress Format - Download content ready for WP import
- [x] Regenerate Section - Regenerate specific H2 section
- [x] Apply Human Touch - Regenerate with more authentic voice

---

## 5. Image Generation (8 functions) ✅
- [x] Generate Featured Image - Create AI image using FLUX 1.1 Pro (human-focused prompts)
- [x] Check Image Status - Poll image creation progress
- [x] Upload Custom Image - Upload your own featured image (auto WebP optimization)
- [x] Auto-Generate Alt Text - Create SEO alt text via Claude Vision (empathetic tone)
- [x] Suggest Alt Text - Get empathetic alt text suggestions
- [x] Edit Alt Text - Modify image alt text manually
- [x] Optimize Image - Compress/convert to WebP (jpg-to-webp CLI script)
- [x] Validate Image - Check image quality and compatibility

---

## 6. SEO & Keywords Phase 2 (4 functions) ✅
- [x] Group Keywords by Healing Stage - Categorize by Discovery/Validation/Action
- [x] Analyze ROI by Journey Phase - Content performance by healing stage
- [x] Tag Content with Journey Phase - Auto-detect or manual stage assignment
- [x] List Journey Phases - Get phase metadata for UI display

## 6B. Social Media / Social Echo (11 functions) ✅

### 6B.1 - Social Echo Tool ✅
- [x] Generate Social Echo - Create Instagram carousel + Facebook post from article
- [x] View Generated Social Posts - See Instagram slides and Facebook copy
- [x] Edit Instagram Carousel - Modify individual slides (Hook, Problem, Solution, Insight, CTA)
- [x] View Repurposing Articles - Browse articles available for social repurposing
- [x] Regenerate Social Snippets - Update social media content

### 6B.2 - Progress Bar Integration ✅
- [x] WebSocket Progress Adapter - Real-time percentage updates to Dev-Cockpit
- [x] Category Broadcasting - social_echo, seo_phase2, image_conversion

### 6B.3 - JPG-to-WebP Integration ✅
- [x] WebP Conversion Adapter - Async wrapper for Pillow optimization
- [x] Single Image Conversion - POST /images/convert/webp
- [x] Batch Conversion - POST /images/convert/webp/batch with progress

---

## 7. WordPress Integration (8 functions) ✅

### 7.1 - Core Integration Functions ✅
- [x] wp_sync_articles - Fetch archive metadata from WordPress
- [x] wp_get_relational_tone - Analyze past posts for Persona calibration
- [x] wp_push_social_outline - Send Instagram Carousel to WP drafts
- [x] wp_journey_mapper - Apply SEO Healing Stage tags to synced posts
- [x] Test WordPress Connection - Verify credentials work correctly

### 7.2 - Advanced Functions ✅
- [x] wp_update_draft_tone - Human Touch Feedback Loop (warmth, you-language, questions)
- [x] wp_fetch_media_library - Link to Category 6B's WebP optimization
- [x] wp_validate_seo_tags - Journey Phase Audit (coverage score, recommendations)

---

## 8.0 Intelligence & Maintenance (3 functions) ✅

### 8.1 - Weekly Performance Card ✅
- [x] Generate Weekly Performance Card with Competitor Gaps
- [x] Calculate journey phase balance scores
- [x] AI-generated narrative (Therapeutic Guide persona)
- [x] Gap closure rate tracking

### 8.2 - Feedback Loop ✅
- [x] Hook 'Regenerate Section' button for Android app feedback
- [x] Support 'More Warmth' feedback type
- [x] Support additional feedback types (professional, concise, detailed, empathetic)
- [x] Integrate feedback prompts with AI regeneration

### 8.3 - Cleanup Routine ✅
- [x] 30-day purge script for competitor_scrapes table
- [x] Dry-run mode (default) for safety
- [x] Gemini safety validation completed

---

## 8. Google Search Console (8 functions) ✅

### 8.1 - OAuth2 Integration (Gemini Security Validated) ✅
- [x] Get Auth URL - OAuth2 authorization URL with CSRF state
- [x] OAuth Callback - Server-side token exchange with encryption
- [x] Token Refresh - Automatic rotation with 5-min buffer
- [x] Revocation Handling - Cleanup on token revocation
- [x] View Connected Sites - List all GSC properties
- [x] Disconnect GSC - Remove GSC connection

### 8.2 - Search Analytics with Journey Mapping ✅
- [x] Fetch GSC Data - Get query performance metrics
- [x] Journey Phase Mapping - Map queries to Discovery/Validation/Action
- [x] Journey Heatmap - Real-time Healing Stage distribution for Android
- [x] Analyze Opportunities - Identify low-hanging fruit keywords

### 8.3 - Filters & Configuration ✅
- [x] Set GSC Filters - Define min impressions, position, date range
- [x] View Current Filters - Check active filter settings
- [x] Check GSC Status - Connection and token validity status

---

## 9. Knowledge Vault / RAG (7 functions) ✅

### 9.1 - Vault Core (ChromaDB) ✅
- [x] Upload Document - Add PDF/text to knowledge base
- [x] Ingest Document - Process text content into chunks with embeddings
- [x] Query Knowledge Base - Semantic search for relevant content
- [x] View Knowledge Stats - Document count, chunks, storage usage
- [x] Delete Document - Remove document from knowledge base
- [x] Get Context - RAG context injection for Social Echo and Regenerate Section

### 9.2 - WordPress Sync ✅
- [x] Sync WordPress Private - Sync PDFs/notes from WP Private category

### 9.3 - Context Injection (Gemini Validated) ✅
- [x] Social Echo context injection - Pulls methodology context for carousel generation
- [x] Regenerate Section context injection - Injects vault context into refinement

---

## 10. ROI & Growth Analytics (10 functions) ✅

### 10.1 - Therapeutic ROI Engine (Gemini Validated) ✅
- [x] Calculate Therapeutic ROI - Action-stage conversion tracking with therapeutic framing
- [x] Track Healing Action - Record steps taken in healing journey (not "conversions")
- [x] Get Community Health - Aggregate ecosystem vitality metrics
- [x] Get Journey Heatmap - Patient Journey distribution visualization

### 10.2 - Growth Velocity ✅
- [x] Calculate Growth Velocity - MoM shifts in Journey Heatmap
- [x] Track Stage Progressions - Movement through healing stages
- [x] Generate Growth Narrative - AI-generated therapeutic growth story

### 10.3 - Executive Quick View (Android Push) ✅
- [x] Get Executive View - One-glance project health summary
- [x] WebSocket Broadcast - Push to S23 Ultra via dev-bridge
- [x] List Action Types - Available step types with therapeutic labels

---

## 11. Settings & System Configuration (12 functions) ✅

### 11.1 - User Settings (Gemini Validated) ✅
- [x] Get User Settings - Fetch all user preferences with graceful degradation
- [x] Update Content Settings - Persona intensity, word counts, excluded topics
- [x] Update Notification Settings - Telegram/WebSocket/Email preferences
- [x] Update Integration Settings - WordPress/GSC/AI configurations
- [x] List Persona Intensities - Available intensity levels with descriptions

### 11.2 - Notification Hub (Rate Limited) ✅
- [x] Notification Hub Service - Central orchestrator with rate limiting
- [x] Telegram Notification Adapter - Bot API integration for milestone alerts
- [x] Get Rate Limit Status - Check notification throttling per channel
- [x] Milestone Templates - Therapeutic messaging for growth achievements

### 11.3 - API Key Rotation (Dual-Key Security) ✅
- [x] Rotate API Keys - Secure rotation for GSC, WordPress, OpenAI, Fernet
- [x] Fernet Dual-Key Migration - PRIMARY/SECONDARY key fallback system
- [x] Reload Secrets - Hot-reload API keys without restart (Admin only)

---

## 12. Billing & Subscription (10 functions) ✅

### 12.1 - Subscription Tier System (Gemini Validated) ✅
- [x] View Billing Status - Current tier, features, limits, renewal info
- [x] View Available Plans - Free/Pro/Elite tiers with pricing
- [x] View Credit Packs - One-time credit purchase options (Starter/Growth/Scale)
- [x] Check Feature Access - Verify tier grants access to specific features
- [x] Check Quota Status - Remaining credits per usage type

### 12.2 - Stripe Integration (Webhook Security Validated) ✅
- [x] Create Checkout Session - Stripe checkout for subscriptions or credits
- [x] Access Billing Portal - Manage subscription, payment method, invoices
- [x] Stripe Webhook Handler - Signature verification, idempotency, event processing
- [x] Handle Subscription Events - checkout.completed, invoice.paid/failed, subscription.updated/deleted

### 12.3 - Usage Tracking ✅
- [x] Track Usage - Record OpenAI tokens, WordPress calls, articles, images
- [x] Get Usage Summary - Monthly usage totals with percentages

---

## 13. Content Quality & Refinement (7 functions) ✅
- [x] Evaluate Authenticity - Check content alignment with persona
- [x] Get Authenticity Score - View persona alignment metrics
- [x] Refine Tone - Quick tone adjustments (warm, professional, casual)
- [x] View Therapeutic Compass - Persona voice alignment visualization
- [x] Analyze Sentiment - Evaluate emotional tone of content
- [x] Generate Link Suggestions - Get internal linking recommendations
- [x] Apply Internal Links - Add suggested internal links to content

---

## 14. Web Frontend - Next.js 14 SaaS (Gemini Validated) ✅

### 14.1 - Project Setup ✅
- [x] Initialize Next.js 14 with App Router
- [x] Configure Tailwind CSS with therapeutic color palette
- [x] Setup Zustand for WebSocket state management
- [x] Create API client for FastAPI backend integration

### 14.2 - Social Echo Workspace ✅
- [x] Persona Intensity Toggle (Supportive/Balanced/Direct)
- [x] Article Selector with healing stage badges
- [x] Instagram Carousel Preview (phone mockup)
- [x] Generate button with loading states
- [x] Export and Push to WP actions

### 14.3 - Patient Journey Heatmap ✅
- [x] Journey distribution bar chart (Recharts)
- [x] Healing balance pie chart
- [x] Discovery/Validation/Action summary cards
- [x] AI-generated therapeutic insights
- [x] Journey Balance Score calculation

### 14.4 - WebSocket Progress Bar ✅
- [x] Global progress bar component (fixed position)
- [x] Real-time percentage updates
- [x] Category badges for task type
- [x] Connection status indicator
- [x] Auto-dismiss on completion

---

## 15. Admin Dashboard - Superusers Only (10 functions) ✅
- [x] View All Users - Admin list of all system users
- [x] Check Admin Status - Verify superuser privileges
- [x] Update User - Modify user tier, credits, or settings
- [x] Delete User - Remove user from system
- [x] View User Connections - See user's integrations (GSC, WP)
- [x] Cleanup Stale Data - Remove orphaned/old records
- [x] Send Summary Email - Manually send weekly summary to user
- [x] Preview Summary - See what summary email will contain
- [x] Send Summaries Batch - Email weekly summaries to all users
- [x] Gold Pulse Admin Badge - Animated indicator when workforce is online

---

## 16. System Scaffolding & Utility (4 functions) ✅
- [x] Health Check - Verify API availability with DB check
- [x] Validate Auth Token - Check if JWT is still valid
- [x] Send Test Report - Email test strategy report
- [x] Database Migrations - Alembic setup
- [x] Testing Framework - Pytest fixtures and integration tests

---

## 17. System Audit & Remediation (In Progress)
- [x] Comprehensive Audit - Run by Claude [cite: 2026-02-18]
- [x] Fix Unregistered Routes (Critical) - seo.py, images.py
- [x] Fix Missing Frontend Pages (High) - /content, /analytics, /settings
- [ ] Implement Dependency Injection (High) - Resolve 45+ TODOs
- [ ] Clean Up Orphans (Low) - ProgressBar.tsx

---

## 18. Deployment Preparation (4 Functions) ✅
- [x] Backend Containerization - Dockerfile & docker-compose.yml
- [x] Frontend Deployment Config - vercel.json & Dockerfile
- [x] Environment Configuration - .env.example & secret gen script
- [x] Production Entry Point - start_prod.sh

---

## Summary

| Category | Functions | Status |
|----------|-----------|--------|
| Onboarding & Setup | 11 | **Complete** ✅ |
| Dashboard | 8 | **Complete** ✅ |
| Content Generation | 9 | **Complete** ✅ |
| Content Management | 12 | **Complete** ✅ |
| Image Generation | 8 | **Complete** ✅ |
| SEO & Keywords Phase 2 | 4 | **Complete** ✅ |
| Social Media (6B) | 11 | **Complete** ✅ |
| WordPress Integration | 8 | **Complete** ✅ |
| Intelligence & Maintenance (8.0) | 3 | **Complete** ✅ |
| Google Search Console | 8 | **Complete** ✅ |
| Knowledge Vault | 7 | **Complete** ✅ |
| ROI & Growth Analytics | 10 | **Complete** ✅ |
| Settings & System Config | 12 | **Complete** ✅ |
| Billing & Subscription | 10 | **Complete** ✅ |
| Content Quality (13) | 7 | **Complete** ✅ |
| Web Frontend (Next.js 14) | 15 | **Complete** ✅ |
| Admin Dashboard (15) | 10 | **Complete** ✅ |
| System & Utility (16) | 4 | **Complete** ✅ |
| Audit & Remediation (17) | - | **In Progress** 🏗️ |
| Deployment Prep (18) | 4 | **Complete** ✅ |
| **Total** | **~184** | **CORE COMPLETE** |

---

*Last Updated: 2026-02-19*
*Backend: http://localhost:8000 | Frontend: http://localhost:3000*
