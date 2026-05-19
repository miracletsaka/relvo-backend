--
-- PostgreSQL database dump
--

\restrict 1o3E3cEQhAFnWSPGQr8rKpcmryDdVajL1Rpp62fzDgYEm1IpNuq7LTgy5fXIb3n

-- Dumped from database version 17.9 (Ubuntu 17.9-0ubuntu0.25.10.1)
-- Dumped by pg_dump version 17.9 (Ubuntu 17.9-0ubuntu0.25.10.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: media_asset_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.media_asset_type AS ENUM (
    'image',
    'video'
);


--
-- Name: media_category; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.media_category AS ENUM (
    'whatsapp_automation',
    'chatbots',
    'websites',
    'web_apps',
    'general'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: approvals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.approvals (
    id uuid NOT NULL,
    content_item_id uuid NOT NULL,
    decision character varying(20) NOT NULL,
    reason text,
    decided_by character varying(100) NOT NULL,
    decided_at timestamp without time zone NOT NULL
);


--
-- Name: brand_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.brand_profiles (
    brand_id character varying(100) NOT NULL,
    website_url character varying(1500),
    status character varying(30) NOT NULL,
    last_error text,
    last_scraped_at timestamp without time zone,
    pages_scraped jsonb,
    raw_text text,
    profile_json jsonb,
    profile_summary text,
    colors jsonb,
    tone_tags jsonb,
    services jsonb,
    positioning text,
    audiences jsonb,
    cta_examples jsonb,
    notes_manual_override text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: brands; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.brands (
    id character varying(100) NOT NULL,
    display_name character varying(200) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    org_id uuid NOT NULL,
    tones text[] DEFAULT ARRAY[]::text[],
    logo_url text,
    primary_color character varying(20) DEFAULT '#7c3aed'::character varying
);


--
-- Name: content_drafts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.content_drafts (
    id uuid NOT NULL,
    topic_chat_id uuid NOT NULL,
    brand_id character varying NOT NULL,
    platform character varying NOT NULL,
    status character varying DEFAULT 'PENDING_APPROVAL'::character varying NOT NULL,
    body_text text,
    hashtags text,
    structured jsonb,
    scheduled_at timestamp without time zone,
    last_error text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    media_type character varying,
    media_url text,
    media_urls text,
    thumbnail_url text,
    media_provider character varying,
    media_caption text,
    org_id uuid NOT NULL,
    tone character varying(50) DEFAULT NULL::character varying,
    tone_id uuid
);


--
-- Name: content_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.content_items (
    id uuid NOT NULL,
    brand_id character varying NOT NULL,
    platform character varying NOT NULL,
    topic text NOT NULL,
    plan_month character varying(7) NOT NULL,
    times_per_week integer NOT NULL,
    status character varying DEFAULT 'TOPIC_INGESTED'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    org_id uuid NOT NULL
);


--
-- Name: email_verification_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_verification_tokens (
    token character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone
);


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    id uuid NOT NULL,
    content_item_id uuid NOT NULL,
    job_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    attempts integer NOT NULL,
    last_error text,
    created_at timestamp without time zone NOT NULL,
    org_id uuid
);


--
-- Name: media_assets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media_assets (
    id uuid NOT NULL,
    url character varying NOT NULL,
    filename character varying NOT NULL,
    type public.media_asset_type NOT NULL,
    tags json,
    size_bytes integer,
    mime_type character varying,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    brand_id character varying,
    brand_name character varying,
    width integer,
    height integer,
    org_id uuid,
    price numeric(10,2) DEFAULT NULL::numeric,
    price_currency character varying(3) DEFAULT 'USD'::character varying,
    title character varying(200),
    description text,
    compare_at_price numeric(12,2),
    discount_label character varying(100),
    offer_title character varying(200),
    offer_description text,
    cta_text character varying(80),
    cta_url text,
    availability character varying(50) DEFAULT 'available'::character varying,
    product_category character varying(120),
    service_area character varying(200),
    features jsonb DEFAULT '[]'::jsonb,
    metadata jsonb DEFAULT '{}'::jsonb
);


--
-- Name: org_accreditations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_accreditations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    issuer character varying(200),
    year integer,
    logo_url text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: org_business_info; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_business_info (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    business_type character varying(100),
    founded_year integer,
    company_size character varying(50),
    website character varying(500),
    address text,
    tagline character varying(300),
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    email_primary character varying(320),
    email_support character varying(320),
    phone_primary character varying(30),
    phone_secondary character varying(30),
    whatsapp character varying(30),
    country character varying(100),
    city character varying(100),
    state_province character varying(100),
    postal_code character varying(20),
    map_url character varying(1000),
    facebook_url character varying(500),
    instagram_url character varying(500),
    linkedin_url character varying(500),
    twitter_url character varying(500),
    tiktok_url character varying(500),
    youtube_url character varying(500),
    registration_no character varying(100),
    vat_number character varying(100)
);


--
-- Name: org_campaign_goals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_campaign_goals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    label character varying(200) NOT NULL,
    is_preset boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: org_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_images (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    type character varying(20) DEFAULT 'gallery'::character varying NOT NULL,
    url text NOT NULL,
    caption character varying(300),
    sort_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: org_metadata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_metadata (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    key character varying(200) NOT NULL,
    value text NOT NULL,
    category character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: org_offers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_offers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    title character varying(300) NOT NULL,
    description text,
    cta_text character varying(100),
    cta_url character varying(500),
    expires_at date,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: org_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_reviews (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    author_name character varying(200) NOT NULL,
    rating double precision NOT NULL,
    body text,
    source character varying(100),
    review_date date,
    is_featured boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    reviewer_email character varying(320),
    reviewer_photo_url text,
    product_image_url text,
    card_image_url text,
    card_status character varying(20) DEFAULT 'pending'::character varying,
    CONSTRAINT org_reviews_rating_check CHECK (((rating >= (1)::double precision) AND (rating <= (5)::double precision)))
);


--
-- Name: org_sponsors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_sponsors (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    logo_url text,
    website character varying(500),
    sort_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: organisation_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organisation_members (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role character varying(20) DEFAULT 'member'::character varying NOT NULL,
    invited_by uuid,
    joined_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: organisations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organisations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    plan character varying(50) DEFAULT 'free'::character varying NOT NULL,
    stripe_customer_id character varying(100),
    stripe_subscription_id character varying(100),
    plan_expires_at timestamp with time zone,
    max_brands integer,
    max_platforms integer,
    max_drafts_pm integer,
    max_renders_pm integer,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    logo_url text
);


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: platform_orientations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platform_orientations (
    platform_id character varying NOT NULL,
    orientation character varying(10) DEFAULT 'portrait'::character varying NOT NULL,
    org_id uuid NOT NULL
);


--
-- Name: platforms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platforms (
    id character varying(50) NOT NULL,
    display_name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    org_id uuid NOT NULL
);


--
-- Name: review_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_requests (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    sent_by uuid,
    email character varying(320) NOT NULL,
    sent_at timestamp with time zone DEFAULT now() NOT NULL,
    opened_at timestamp with time zone,
    reviewed_at timestamp with time zone
);


--
-- Name: review_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    email character varying(320) NOT NULL,
    token_hash character varying(128) NOT NULL,
    used_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: template_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.template_metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    template_id character varying NOT NULL,
    views integer DEFAULT 0,
    clicks integer DEFAULT 0,
    conversions integer DEFAULT 0
);


--
-- Name: template_serves; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.template_serves (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    template_id character varying NOT NULL,
    org_id uuid NOT NULL,
    brand_id character varying,
    tone_id uuid,
    orientation character varying(10),
    served_at timestamp without time zone DEFAULT now()
);


--
-- Name: templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.templates (
    id character varying NOT NULL,
    brand_id character varying,
    name character varying NOT NULL,
    description text,
    shapes_json text NOT NULL,
    canvas_width character varying NOT NULL,
    canvas_height character varying NOT NULL,
    background_image text,
    logo_placement_json text,
    thumbnail_url text,
    preview_url text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    org_id uuid NOT NULL,
    orientation character varying(10) DEFAULT 'portrait'::character varying,
    tone_id uuid
);


--
-- Name: tones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tones (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    label character varying(150) NOT NULL,
    description text,
    emoji character varying(10),
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: topic_chats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topic_chats (
    id uuid NOT NULL,
    brand_id character varying NOT NULL,
    topic text NOT NULL,
    target_month character varying(7),
    posts_per_week integer,
    timezone character varying DEFAULT 'Africa/Blantyre'::character varying NOT NULL,
    posting_hour_local integer DEFAULT 9 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    background_images jsonb DEFAULT '[]'::jsonb NOT NULL,
    generation_status character varying,
    generation_result json,
    generation_error character varying(500),
    org_id uuid NOT NULL,
    tone_id uuid
);


--
-- Name: topics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topics (
    id uuid NOT NULL,
    brand_id character varying(100) NOT NULL,
    topic_text character varying(1000) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    org_id uuid NOT NULL
);


--
-- Name: usage_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usage_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    user_id uuid,
    action character varying(50) NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    period character varying(7) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    session_token character varying(128) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    user_agent character varying(255),
    ip_address character varying(64),
    org_id uuid
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    is_email_verified boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    first_name character varying(100),
    last_name character varying(100)
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: approvals approvals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_pkey PRIMARY KEY (id);


--
-- Name: brand_profiles brand_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brand_profiles
    ADD CONSTRAINT brand_profiles_pkey PRIMARY KEY (brand_id);


--
-- Name: brands brands_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brands
    ADD CONSTRAINT brands_pkey PRIMARY KEY (id);


--
-- Name: content_drafts content_drafts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_drafts
    ADD CONSTRAINT content_drafts_pkey PRIMARY KEY (id);


--
-- Name: content_items content_items_v1_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_items
    ADD CONSTRAINT content_items_v1_pkey PRIMARY KEY (id);


--
-- Name: email_verification_tokens email_verification_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_verification_tokens
    ADD CONSTRAINT email_verification_tokens_pkey PRIMARY KEY (token);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: media_assets media_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_assets
    ADD CONSTRAINT media_assets_pkey PRIMARY KEY (id);


--
-- Name: org_accreditations org_accreditations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_accreditations
    ADD CONSTRAINT org_accreditations_pkey PRIMARY KEY (id);


--
-- Name: org_business_info org_business_info_org_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_business_info
    ADD CONSTRAINT org_business_info_org_id_key UNIQUE (org_id);


--
-- Name: org_business_info org_business_info_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_business_info
    ADD CONSTRAINT org_business_info_pkey PRIMARY KEY (id);


--
-- Name: org_campaign_goals org_campaign_goals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_campaign_goals
    ADD CONSTRAINT org_campaign_goals_pkey PRIMARY KEY (id);


--
-- Name: org_images org_images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_images
    ADD CONSTRAINT org_images_pkey PRIMARY KEY (id);


--
-- Name: org_metadata org_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_metadata
    ADD CONSTRAINT org_metadata_pkey PRIMARY KEY (id);


--
-- Name: org_offers org_offers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_offers
    ADD CONSTRAINT org_offers_pkey PRIMARY KEY (id);


--
-- Name: org_reviews org_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_reviews
    ADD CONSTRAINT org_reviews_pkey PRIMARY KEY (id);


--
-- Name: org_sponsors org_sponsors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_sponsors
    ADD CONSTRAINT org_sponsors_pkey PRIMARY KEY (id);


--
-- Name: organisation_members organisation_members_org_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation_members
    ADD CONSTRAINT organisation_members_org_id_user_id_key UNIQUE (org_id, user_id);


--
-- Name: organisation_members organisation_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation_members
    ADD CONSTRAINT organisation_members_pkey PRIMARY KEY (id);


--
-- Name: organisations organisations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisations
    ADD CONSTRAINT organisations_pkey PRIMARY KEY (id);


--
-- Name: organisations organisations_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisations
    ADD CONSTRAINT organisations_slug_key UNIQUE (slug);


--
-- Name: organisations organisations_stripe_customer_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisations
    ADD CONSTRAINT organisations_stripe_customer_id_key UNIQUE (stripe_customer_id);


--
-- Name: organisations organisations_stripe_subscription_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisations
    ADD CONSTRAINT organisations_stripe_subscription_id_key UNIQUE (stripe_subscription_id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: platform_orientations platform_orientations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_orientations
    ADD CONSTRAINT platform_orientations_pkey PRIMARY KEY (platform_id);


--
-- Name: platforms platforms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platforms
    ADD CONSTRAINT platforms_pkey PRIMARY KEY (id, org_id);


--
-- Name: review_requests review_requests_org_id_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_org_id_email_key UNIQUE (org_id, email);


--
-- Name: review_requests review_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_pkey PRIMARY KEY (id);


--
-- Name: review_tokens review_tokens_org_id_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_tokens
    ADD CONSTRAINT review_tokens_org_id_email_key UNIQUE (org_id, email);


--
-- Name: review_tokens review_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_tokens
    ADD CONSTRAINT review_tokens_pkey PRIMARY KEY (id);


--
-- Name: review_tokens review_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_tokens
    ADD CONSTRAINT review_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: template_metrics template_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_metrics
    ADD CONSTRAINT template_metrics_pkey PRIMARY KEY (id);


--
-- Name: template_serves template_serves_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_serves
    ADD CONSTRAINT template_serves_pkey PRIMARY KEY (id);


--
-- Name: templates templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_pkey PRIMARY KEY (id);


--
-- Name: tones tones_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tones
    ADD CONSTRAINT tones_name_key UNIQUE (name);


--
-- Name: tones tones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tones
    ADD CONSTRAINT tones_pkey PRIMARY KEY (id);


--
-- Name: topic_chats topic_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_chats
    ADD CONSTRAINT topic_chats_pkey PRIMARY KEY (id);


--
-- Name: topics topics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_pkey PRIMARY KEY (id);


--
-- Name: usage_logs usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_logs
    ADD CONSTRAINT usage_logs_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_brands_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_brands_org_id ON public.brands USING btree (org_id);


--
-- Name: idx_content_drafts_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_content_drafts_org_id ON public.content_drafts USING btree (org_id);


--
-- Name: idx_content_items_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_content_items_org_id ON public.content_items USING btree (org_id);


--
-- Name: idx_media_assets_brand_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_media_assets_brand_id ON public.media_assets USING btree (brand_id);


--
-- Name: idx_media_assets_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_media_assets_org_id ON public.media_assets USING btree (org_id);


--
-- Name: idx_org_members_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_members_org_id ON public.organisation_members USING btree (org_id);


--
-- Name: idx_org_members_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_members_user_id ON public.organisation_members USING btree (user_id);


--
-- Name: idx_organisations_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organisations_slug ON public.organisations USING btree (slug);


--
-- Name: idx_platforms_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_platforms_org_id ON public.platforms USING btree (org_id);


--
-- Name: idx_templates_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_templates_org_id ON public.templates USING btree (org_id);


--
-- Name: idx_topic_chats_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_topic_chats_org_id ON public.topic_chats USING btree (org_id);


--
-- Name: idx_topics_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_topics_org_id ON public.topics USING btree (org_id);


--
-- Name: idx_usage_logs_org_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_logs_org_period ON public.usage_logs USING btree (org_id, period);


--
-- Name: idx_user_sessions_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_sessions_org_id ON public.user_sessions USING btree (org_id);


--
-- Name: ix_content_drafts_brand_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_drafts_brand_id ON public.content_drafts USING btree (brand_id);


--
-- Name: ix_content_drafts_platform; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_drafts_platform ON public.content_drafts USING btree (platform);


--
-- Name: ix_content_drafts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_drafts_status ON public.content_drafts USING btree (status);


--
-- Name: ix_content_drafts_tone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_drafts_tone ON public.content_drafts USING btree (tone);


--
-- Name: ix_content_drafts_topic_chat_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_drafts_topic_chat_id ON public.content_drafts USING btree (topic_chat_id);


--
-- Name: ix_email_token_user_exp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_token_user_exp ON public.email_verification_tokens USING btree (user_id, expires_at);


--
-- Name: ix_email_verification_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_verification_tokens_user_id ON public.email_verification_tokens USING btree (user_id);


--
-- Name: ix_org_accreditations_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_accreditations_org_id ON public.org_accreditations USING btree (org_id);


--
-- Name: ix_org_business_info_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_business_info_org_id ON public.org_business_info USING btree (org_id);


--
-- Name: ix_org_campaign_goals_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_campaign_goals_org_id ON public.org_campaign_goals USING btree (org_id);


--
-- Name: ix_org_images_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_images_org_id ON public.org_images USING btree (org_id);


--
-- Name: ix_org_images_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_images_type ON public.org_images USING btree (org_id, type);


--
-- Name: ix_org_metadata_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_metadata_org_id ON public.org_metadata USING btree (org_id);


--
-- Name: ix_org_offers_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_offers_org_id ON public.org_offers USING btree (org_id);


--
-- Name: ix_org_reviews_card_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_reviews_card_status ON public.org_reviews USING btree (card_status) WHERE ((card_status)::text = 'pending'::text);


--
-- Name: ix_org_reviews_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_reviews_org_id ON public.org_reviews USING btree (org_id);


--
-- Name: ix_org_sponsors_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_sponsors_org_id ON public.org_sponsors USING btree (org_id);


--
-- Name: ix_password_reset_tokens_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_reset_tokens_token ON public.password_reset_tokens USING btree (token);


--
-- Name: ix_password_reset_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_reset_tokens_user_id ON public.password_reset_tokens USING btree (user_id);


--
-- Name: ix_review_requests_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_requests_org_id ON public.review_requests USING btree (org_id);


--
-- Name: ix_review_tokens_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_tokens_hash ON public.review_tokens USING btree (token_hash);


--
-- Name: ix_review_tokens_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_tokens_org_id ON public.review_tokens USING btree (org_id);


--
-- Name: ix_sessions_user_exp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sessions_user_exp ON public.user_sessions USING btree (user_id, expires_at);


--
-- Name: ix_templates_brand_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_templates_brand_id ON public.templates USING btree (brand_id);


--
-- Name: ix_templates_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_templates_org_id ON public.templates USING btree (org_id);


--
-- Name: ix_tones_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tones_is_active ON public.tones USING btree (is_active);


--
-- Name: ix_tones_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tones_name ON public.tones USING btree (name);


--
-- Name: ix_topic_chats_brand_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_topic_chats_brand_id ON public.topic_chats USING btree (brand_id);


--
-- Name: ix_user_sessions_session_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_user_sessions_session_token ON public.user_sessions USING btree (session_token);


--
-- Name: ix_user_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_sessions_user_id ON public.user_sessions USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: brands brands_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brands
    ADD CONSTRAINT brands_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: content_drafts content_drafts_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_drafts
    ADD CONSTRAINT content_drafts_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: content_drafts content_drafts_tone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_drafts
    ADD CONSTRAINT content_drafts_tone_id_fkey FOREIGN KEY (tone_id) REFERENCES public.tones(id) ON DELETE SET NULL;


--
-- Name: content_drafts content_drafts_topic_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_drafts
    ADD CONSTRAINT content_drafts_topic_chat_id_fkey FOREIGN KEY (topic_chat_id) REFERENCES public.topic_chats(id) ON DELETE CASCADE;


--
-- Name: content_items content_items_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_items
    ADD CONSTRAINT content_items_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: email_verification_tokens email_verification_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_verification_tokens
    ADD CONSTRAINT email_verification_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: media_assets media_assets_brand_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_assets
    ADD CONSTRAINT media_assets_brand_id_fkey FOREIGN KEY (brand_id) REFERENCES public.brands(id) ON DELETE SET NULL;


--
-- Name: media_assets media_assets_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_assets
    ADD CONSTRAINT media_assets_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_accreditations org_accreditations_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_accreditations
    ADD CONSTRAINT org_accreditations_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_business_info org_business_info_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_business_info
    ADD CONSTRAINT org_business_info_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_campaign_goals org_campaign_goals_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_campaign_goals
    ADD CONSTRAINT org_campaign_goals_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_images org_images_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_images
    ADD CONSTRAINT org_images_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_metadata org_metadata_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_metadata
    ADD CONSTRAINT org_metadata_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_offers org_offers_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_offers
    ADD CONSTRAINT org_offers_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_reviews org_reviews_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_reviews
    ADD CONSTRAINT org_reviews_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: org_sponsors org_sponsors_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_sponsors
    ADD CONSTRAINT org_sponsors_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: organisation_members organisation_members_invited_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation_members
    ADD CONSTRAINT organisation_members_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: organisation_members organisation_members_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation_members
    ADD CONSTRAINT organisation_members_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: organisation_members organisation_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation_members
    ADD CONSTRAINT organisation_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: platform_orientations platform_orientations_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_orientations
    ADD CONSTRAINT platform_orientations_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: platform_orientations platform_orientations_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_orientations
    ADD CONSTRAINT platform_orientations_platform_id_fkey FOREIGN KEY (platform_id, org_id) REFERENCES public.platforms(id, org_id) ON DELETE CASCADE;


--
-- Name: platforms platforms_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platforms
    ADD CONSTRAINT platforms_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: review_requests review_requests_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: review_requests review_requests_sent_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_sent_by_fkey FOREIGN KEY (sent_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: review_tokens review_tokens_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_tokens
    ADD CONSTRAINT review_tokens_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: templates templates_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: templates templates_tone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_tone_id_fkey FOREIGN KEY (tone_id) REFERENCES public.tones(id) ON DELETE SET NULL;


--
-- Name: topic_chats topic_chats_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_chats
    ADD CONSTRAINT topic_chats_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: topic_chats topic_chats_tone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_chats
    ADD CONSTRAINT topic_chats_tone_id_fkey FOREIGN KEY (tone_id) REFERENCES public.tones(id) ON DELETE SET NULL;


--
-- Name: topics topics_brand_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_brand_id_fkey FOREIGN KEY (brand_id) REFERENCES public.brands(id) ON DELETE RESTRICT;


--
-- Name: topics topics_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: usage_logs usage_logs_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_logs
    ADD CONSTRAINT usage_logs_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE CASCADE;


--
-- Name: usage_logs usage_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_logs
    ADD CONSTRAINT usage_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_sessions user_sessions_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisations(id) ON DELETE SET NULL;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 1o3E3cEQhAFnWSPGQr8rKpcmryDdVajL1Rpp62fzDgYEm1IpNuq7LTgy5fXIb3n

