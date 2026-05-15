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
  display_name: string | null;
  is_archived: boolean;
  points_balance: number;
  created_at: string;
  updated_at: string;
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

export interface ProgramRead {
  id: UUID;
  partner_id: UUID;
  name: string;
  description: string | null;
  type: ProgramType;
  accrual_rule: Record<string, unknown>;
  points_ttl_days: number | null;
  min_redemption: number;
  status: ProgramStatus;
  created_at: string;
  updated_at: string;
}

export interface ProgramCreate {
  name: string;
  description?: string | null;
  type: ProgramType;
  accrual_rule: Record<string, unknown>;
  points_ttl_days?: number | null;
  min_redemption?: number;
}

export interface ProgramUpdate {
  name?: string | null;
  description?: string | null;
  accrual_rule?: Record<string, unknown> | null;
  points_ttl_days?: number | null;
  min_redemption?: number | null;
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
  program_name: string;
  program_type: ProgramType;
  program_status: ProgramStatus;
  accrual_rule: Record<string, unknown>;
  min_redemption: number;
  display_name: string | null;
  points_balance: number;
  rewards: RewardOption[];
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
}
