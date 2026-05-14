import { Injectable, signal } from '@angular/core';

export type PageActionIcon = 'edit' | 'archive' | 'unarchive' | 'trash';

export interface PageAction {
  id: string;
  icon: PageActionIcon;
  label: string;
  danger?: boolean;
  disabled?: boolean;
  handler: () => void;
}

@Injectable({ providedIn: 'root' })
export class PageActionsService {
  readonly actions = signal<PageAction[]>([]);

  set(actions: PageAction[]): void {
    this.actions.set(actions);
  }

  clear(): void {
    this.actions.set([]);
  }
}
