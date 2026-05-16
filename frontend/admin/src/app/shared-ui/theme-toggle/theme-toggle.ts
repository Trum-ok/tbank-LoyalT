import { Component, inject } from '@angular/core';

import { ThemeService } from '../../core/theme.service';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  template: `
    <button
      type="button"
      class="theme-toggle"
      [class.is-dark]="theme.isDark()"
      (click)="theme.toggle()"
      [attr.aria-label]="theme.isDark() ? 'Светлая тема' : 'Тёмная тема'"
      [title]="theme.isDark() ? 'Светлая тема' : 'Тёмная тема'"
    >
      @if (theme.isDark()) {
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <circle cx="12" cy="12" r="4" fill="currentColor" />
          <g stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M12 3v2" />
            <path d="M12 19v2" />
            <path d="M3 12h2" />
            <path d="M19 12h2" />
            <path d="M5.6 5.6l1.4 1.4" />
            <path d="M17 17l1.4 1.4" />
            <path d="M5.6 18.4L7 17" />
            <path d="M17 7l1.4-1.4" />
          </g>
        </svg>
      } @else {
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path
            d="M20 14.5A8 8 0 0 1 9.5 4a1 1 0 0 0-1.3-1.3 10 10 0 1 0 13.1 13.1A1 1 0 0 0 20 14.5z"
            fill="currentColor"
          />
        </svg>
      }
    </button>
  `,
  styles: `
    .theme-toggle {
      width: 32px;
      height: 32px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--tbank-divider);
      background: var(--tbank-surface);
      color: var(--tbank-text);
      border-radius: 999px;
      cursor: pointer;
      transition: background 0.15s ease;

      &:hover {
        background: var(--tbank-surface-2);
      }
    }
  `,
})
export class ThemeToggle {
  protected readonly theme = inject(ThemeService);
}
