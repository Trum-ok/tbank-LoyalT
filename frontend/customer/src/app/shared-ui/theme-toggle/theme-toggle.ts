import { Component, inject } from '@angular/core';

import { ThemeService } from '../../core/theme.service';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  imports: [],
  template: `
    <button
      class="theme-toggle"
      type="button"
      [attr.aria-label]="service.isDark() ? 'Светлая тема' : 'Тёмная тема'"
      (click)="service.toggle()"
    >
      @if (service.isDark()) {
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <circle cx="12" cy="12" r="4.5" fill="currentColor" />
          <g stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="12" y1="2" x2="12" y2="5" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="2" y1="12" x2="5" y2="12" />
            <line x1="19" y1="12" x2="22" y2="12" />
            <line x1="4.5" y1="4.5" x2="6.7" y2="6.7" />
            <line x1="17.3" y1="17.3" x2="19.5" y2="19.5" />
            <line x1="4.5" y1="19.5" x2="6.7" y2="17.3" />
            <line x1="17.3" y1="6.7" x2="19.5" y2="4.5" />
          </g>
        </svg>
      } @else {
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            d="M21 13.5A9 9 0 1 1 10.5 3a7 7 0 0 0 10.5 10.5z"
            fill="currentColor"
          />
        </svg>
      }
    </button>
  `,
  styles: [
    `
      .theme-toggle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border: none;
        background: var(--tui-background-neutral-1);
        color: var(--tui-text-primary);
        cursor: pointer;
        transition: background 0.15s ease;
      }
      .theme-toggle:hover {
        background: var(--tui-background-neutral-1-hover);
      }
    `,
  ],
})
export class ThemeToggle {
  protected readonly service = inject(ThemeService);
}
