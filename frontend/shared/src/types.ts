export type UUID = string;

export type PartnerCategory =
  | 'food'
  | 'beauty'
  | 'retail'
  | 'services'
  | 'entertainment';

export type ProgramType = 'accrual' | 'visit' | 'stamps';

export interface CatalogProgram {
  program_id: UUID;
  partner_id: UUID;
  partner_name: string;
  partner_logo_url: string | null;
  partner_brand_color: string | null;
  category: PartnerCategory;
  program_name: string;
  description: string | null;
  type: ProgramType;
}

export interface CatalogProgramDetail extends CatalogProgram {
  accrual_rule: Record<string, unknown>;
  points_ttl_days: number | null;
  min_redemption: number;
  tiers: TierRead[];
  rewards: RewardRead[];
}

export interface CatalogCategory {
  code: PartnerCategory;
  label: string;
  programs_count: number;
}

export interface EnrollmentRead {
  id: UUID;
  customer_id: UUID;
  program_id: UUID;
  short_code: string;
  display_name: string | null;
  is_archived: boolean;
  points_balance: number;
  created_at: string;
  updated_at: string;
  current_tier: TierRead | null;
  partner_name: string | null;
  partner_logo_url: string | null;
  partner_brand_color: string | null;
  program_name: string | null;
}

export interface EnrollmentCreate {
  program_id: UUID;
  display_name?: string | null;
}

export interface EnrollmentUpdate {
  display_name?: string | null;
  is_archived?: boolean | null;
}

export type TransactionType = 'accrual' | 'redemption' | 'reversal';

export interface TransactionRead {
  id: UUID;
  enrollment_id: UUID;
  customer_id: UUID;
  program_id: UUID;
  partner_id: UUID;
  type: TransactionType;
  points: number;
  purchase_amount: string | null;
  reward_id: UUID | null;
  reverses_id: UUID | null;
  expires_at: string | null;
  is_reversed: boolean;
  description: string | null;
  created_at: string;
}

export type NotificationDeliveryStatus = 'pending' | 'delivered' | 'failed';

export interface NotificationRead {
  id: UUID;
  customer_id: UUID;
  type: string;
  title: string;
  body: string | null;
  payload: Record<string, unknown> | null;
  delivery_status: NotificationDeliveryStatus;
  delivered_at: string | null;
  is_read: boolean;
  created_at: string;
}

// ===== Partner-service =====

export interface AccountRead {
  id: UUID;
  email: string;
  full_name: string | null;
  phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  email: string;
  full_name?: string | null;
  phone?: string | null;
}

export interface AccountUpdate {
  full_name?: string | null;
  phone?: string | null;
}

export type ApplicationStatus = 'pending' | 'approved' | 'rejected';

export interface ApplicationRead {
  id: UUID;
  account_id: UUID;
  business_name: string;
  inn: string;
  category: PartnerCategory;
  contact_email: string;
  contact_phone: string | null;
  description: string | null;
  status: ApplicationStatus;
  decided_at: string | null;
  decided_by: UUID | null;
  decision_comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  business_name: string;
  inn: string;
  category: PartnerCategory;
  contact_email: string;
  contact_phone?: string | null;
  description?: string | null;
}

export interface ApplicationUpdate {
  business_name?: string | null;
  inn?: string | null;
  category?: PartnerCategory | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  description?: string | null;
}

export type PartnerStatus = 'active' | 'suspended' | 'blocked';

export interface PartnerRead {
  id: UUID;
  account_id: UUID;
  application_id: UUID;
  name: string;
  inn: string;
  category: PartnerCategory;
  logo_url: string | null;
  brand_color: string | null;
  contact_email: string;
  contact_phone: string | null;
  status: PartnerStatus;
  created_at: string;
  updated_at: string;
}

export interface PartnerUpdate {
  name?: string | null;
  logo_url?: string | null;
  brand_color?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
}

// ===== Programs / Rewards =====

export type ProgramStatus = 'draft' | 'published' | 'paused' | 'archived';

export interface TierRead {
  id: UUID;
  program_id: UUID;
  name: string;
  threshold_points: number;
  accrual_multiplier: number;
}

export interface TierCreate {
  name: string;
  threshold_points?: number;
  accrual_multiplier?: number;
}

export interface TierUpdate {
  name?: string | null;
  threshold_points?: number | null;
  accrual_multiplier?: number | null;
}

export interface ProgramRead {
  id: UUID;
  partner_id: UUID;
  name: string;
  description: string | null;
  type: ProgramType;
  accrual_rule: Record<string, unknown>;
  points_ttl_days: number | null;
  expire_warn_days: number | null;
  min_redemption: number;
  status: ProgramStatus;
  created_at: string;
  updated_at: string;
  // Бонусные механики
  welcome_bonus_points: number | null;
  birthday_bonus_points: number | null;
  birthday_bonus_days: number;
  referral_bonus_points: number | null;
  // Ограничения начисления / списания
  min_purchase_amount: number | null;
  max_points_per_transaction: number | null;
  max_redemption_percent: number | null;
  // Период действия
  valid_from: string | null;
  valid_until: string | null;
  // Уровни лояльности
  tiers: TierRead[];
}

export interface ProgramCreate {
  name: string;
  description?: string | null;
  type: ProgramType;
  accrual_rule: Record<string, unknown>;
  points_ttl_days?: number | null;
  expire_warn_days?: number | null;
  min_redemption?: number;
  welcome_bonus_points?: number | null;
  birthday_bonus_points?: number | null;
  birthday_bonus_days?: number;
  referral_bonus_points?: number | null;
  min_purchase_amount?: number | null;
  max_points_per_transaction?: number | null;
  max_redemption_percent?: number | null;
  valid_from?: string | null;
  valid_until?: string | null;
}

export interface ProgramUpdate {
  name?: string | null;
  description?: string | null;
  accrual_rule?: Record<string, unknown> | null;
  points_ttl_days?: number | null;
  expire_warn_days?: number | null;
  min_redemption?: number | null;
  welcome_bonus_points?: number | null;
  birthday_bonus_points?: number | null;
  birthday_bonus_days?: number | null;
  referral_bonus_points?: number | null;
  min_purchase_amount?: number | null;
  max_points_per_transaction?: number | null;
  max_redemption_percent?: number | null;
  valid_from?: string | null;
  valid_until?: string | null;
}

export type RewardType =
  | 'discount_percent'
  | 'discount_fixed'
  | 'free_item'
  | 'cashback_boost';

export interface RewardRead {
  id: UUID;
  program_id: UUID;
  title: string;
  description: string | null;
  cost_points: number;
  type: RewardType;
  value: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RewardCreate {
  title: string;
  description?: string | null;
  cost_points: number;
  type: RewardType;
  value: Record<string, unknown>;
  is_active?: boolean;
}

export interface RewardUpdate {
  title?: string | null;
  description?: string | null;
  cost_points?: number | null;
  value?: Record<string, unknown> | null;
  is_active?: boolean | null;
}

// ===== Staff / касса =====

export interface StaffRead {
  id: UUID;
  partner_id: UUID;
  name: string;
  login_code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StaffCreate {
  name: string;
  login_code: string;
  pin: string;
}

export interface StaffUpdate {
  name?: string | null;
  pin?: string | null;
  is_active?: boolean | null;
}

export interface StaffLoginRequest {
  login_code: string;
  pin: string;
}

export interface StaffLoginResponse {
  access_token: string;
  token_type: string;
  staff_id: UUID;
  staff_name: string;
  partner_id: UUID;
  partner_name: string;
}

export interface RewardOption {
  id: UUID;
  title: string;
  description: string | null;
  cost_points: number;
  type: RewardType;
}

export interface EnrollmentLookup {
  enrollment_id: UUID;
  customer_id: UUID;
  program_id: UUID;
  short_code: string;
  program_name: string;
  program_type: ProgramType;
  program_status: ProgramStatus;
  accrual_rule: Record<string, unknown>;
  min_redemption: number;
  points_balance: number;
  rewards: RewardOption[];
  current_tier: TierRead | null;
}

export interface AccruePayload {
  customer_id: UUID;
  program_id: UUID;
  purchase_amount?: number;
  points?: number;
  visits?: number;
  description?: string | null;
}

export interface RedeemPayload {
  customer_id: UUID;
  program_id: UUID;
  reward_id: UUID;
  description?: string | null;
}

export interface PointsOperationResult {
  transaction: TransactionRead;
  balance_after: number;
  current_tier: TierRead | null;
}

export type AnalyticsPeriod = '1d' | '7d' | '14d' | '30d' | '90d' | 'all';

export interface AnalyticsDayCount {
  date: string;
  count: number;
}

export interface AnalyticsPurchasesPerUserDay {
  date: string;
  purchases: number;
  users: number;
  ratio: number;
}

export interface AnalyticsSummary {
  active_customers: number;
  accrued: number;
  redeemed: number;
  average_check: number;
}

export interface AnalyticsStickiness {
  dau: number;
  wau: number;
  mau: number;
  dau_wau_pct: number;
  dau_mau_pct: number;
}

export interface AnalyticsRetentionPoint {
  day: number;
  retention: number;
}

export interface AnalyticsRetention {
  cohort_size: number;
  d1: number | null;
  d7: number | null;
  d30: number | null;
  curve: AnalyticsRetentionPoint[];
  median_churn_day: number | null;
}

export interface AnalyticsHeatCell {
  dow: number;
  hour: number;
  count: number;
}

export interface AnalyticsHeatmap {
  max: number;
  cells: AnalyticsHeatCell[];
}

export interface AnalyticsRead {
  period: AnalyticsPeriod;
  summary: AnalyticsSummary;
  new_users_by_day: AnalyticsDayCount[];
  purchases_per_user_by_day: AnalyticsPurchasesPerUserDay[];
  stickiness: AnalyticsStickiness;
  retention: AnalyticsRetention;
  heatmap: AnalyticsHeatmap;
}

export type BroadcastSegment =
  | 'all_enrolled'
  | 'active_30d'
  | 'by_program'
  | 'balance_positive'
  | 'new_7d';

export type BroadcastStatus = 'draft' | 'sent' | 'failed';

export interface BroadcastRead {
  id: UUID;
  partner_id: UUID;
  title: string;
  body: string;
  segment: BroadcastSegment;
  program_id: UUID | null;
  status: BroadcastStatus;
  audience_count: number | null;
  sent_count: number | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BroadcastCreate {
  title: string;
  body: string;
  segment: BroadcastSegment;
  program_id?: UUID | null;
}

export interface BroadcastUpdate {
  title?: string;
  body?: string;
  segment?: BroadcastSegment;
  program_id?: UUID | null;
}

export interface AudiencePreview {
  count: number;
}

// ===== Admin-service =====

export interface AdminRead {
  id: UUID;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminCreate {
  email: string;
  full_name?: string | null;
}

export interface AdminUpdate {
  full_name?: string | null;
  is_active?: boolean | null;
}

export interface AdminPartnersOverview {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  pending_applications: number;
}

export interface AdminCustomersOverview {
  total: number;
  enrolled: number;
}

export interface AdminTransactionsOverview {
  accruals_count: number;
  accruals_points: number;
  redemptions_count: number;
  redemptions_points: number;
  reversals_count: number;
}

export interface AdminPlatformOverview {
  partners: AdminPartnersOverview;
  customers: AdminCustomersOverview;
  transactions: AdminTransactionsOverview;
}

export interface AdminTopPartner {
  partner_id: UUID;
  partner_name: string;
  transactions_count: number;
  customers_count: number;
}

export interface AdminDailyCount {
  day: string;
  count: number;
}

export interface AdminCategoryRead {
  code: string;
  label: string;
  description: string | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminCategoryUpsert {
  label: string;
  description?: string | null;
  display_order?: number;
  is_active?: boolean;
}

export interface AdminFeaturedPartnerRead {
  id: UUID;
  partner_id: UUID;
  position: number;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminFeaturedPartnerCreate {
  partner_id: UUID;
  position?: number;
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface AdminBannerRead {
  id: UUID;
  title: string;
  body: string | null;
  image_url: string | null;
  link_url: string | null;
  position: number;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminBannerCreate {
  title: string;
  body?: string | null;
  image_url?: string | null;
  link_url?: string | null;
  position?: number;
  is_active?: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface AdminBannerUpdate {
  title?: string | null;
  body?: string | null;
  image_url?: string | null;
  link_url?: string | null;
  position?: number | null;
  is_active?: boolean | null;
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface AdminDecisionRequest {
  comment?: string | null;
}

// ===== Бонусные кампании =====

export type TriggerType =
  | 'birthday'
  | 'fixed_date'
  | 'interval'
  | 'inactivity'
  | 'manual';

export interface BonusTriggerRead {
  id: UUID;
  program_id: UUID;
  type: TriggerType;
  name: string;
  points: number;
  is_active: boolean;
  days_before: number | null;
  fire_date: string | null;
  repeat_yearly: boolean;
  interval_days: number | null;
  repeat_interval: boolean;
  created_at: string;
  updated_at: string;
}

export interface BonusTriggerCreate {
  type: TriggerType;
  name: string;
  points: number;
  is_active?: boolean;
  days_before?: number | null;
  fire_date?: string | null;
  repeat_yearly?: boolean;
  interval_days?: number | null;
  repeat_interval?: boolean;
}

export interface BonusTriggerUpdate {
  type?: TriggerType | null;
  name?: string | null;
  points?: number | null;
  is_active?: boolean | null;
  days_before?: number | null;
  fire_date?: string | null;
  repeat_yearly?: boolean | null;
  interval_days?: number | null;
  repeat_interval?: boolean | null;
}

// ===== Профиль клиента =====

export interface CustomerProfileRead {
  birthday: string | null;
}

export interface CustomerProfileUpdate {
  birthday?: string | null;
}
