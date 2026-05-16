import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AdminIdentityService } from '../../core/admin-identity.service';

@Component({
  selector: 'app-admin-switcher',
  standalone: true,
  template: `
    <div class="who">
      <span class="who__dot"></span>
      <span class="who__label">{{ identity.current().label }}</span>
      @if (identity.isAuthenticated()) {
        <button
          type="button"
          class="who__exit"
          (click)="logout()"
          title="Сменить администратора"
        >
          выйти
        </button>
      }
    </div>
  `,
  styles: `
    .who {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 5px 12px;
      border-radius: 999px;
      background: var(--tbank-surface);
      border: 1px solid var(--tbank-divider);
      font-size: 13px;
      font-weight: 600;
      color: var(--tbank-text);
    }

    .who__dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--tbank-green);
    }

    .who__exit {
      background: transparent;
      border: none;
      color: var(--tbank-text-faint);
      cursor: pointer;
      font: inherit;
      font-size: 12px;
      font-weight: 600;
      padding: 0 0 0 4px;
      border-left: 1px solid var(--tbank-divider);

      &:hover {
        color: var(--tbank-red);
      }
    }
  `,
})
export class AdminSwitcher {
  protected readonly identity = inject(AdminIdentityService);
  private readonly router = inject(Router);

  protected logout(): void {
    this.identity.clear();
    this.router.navigate(['/login']);
  }
}
