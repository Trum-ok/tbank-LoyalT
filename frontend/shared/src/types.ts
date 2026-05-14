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
