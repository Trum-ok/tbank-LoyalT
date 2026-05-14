import { Component, inject } from '@angular/core';

import { NotifyService } from '../../core/notify.service';

@Component({
  selector: 'app-toast-host',
  standalone: true,
  template: `
    <div class="toast-host" role="status" aria-live="polite">
      @for (t of notify.toasts(); track t.id) {
        <article class="toast" [class]="'toast--' + t.kind">
          <span class="toast__dot"></span>
          <div class="toast__body">
            <span class="toast__title">{{ t.title }}</span>
            <span class="toast__message">{{ t.message }}</span>
          </div>
          <button
            type="button"
            class="toast__close"
            aria-label="Закрыть"
            (click)="notify.dismiss(t.id)"
          >
            ✕
          </button>
        </article>
      }
    </div>
  `,
  styles: `
    .toast-host {
      position: fixed;
      top: 22px;
      right: 22px;
      z-index: 200;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 360px;
      pointer-events: none;
    }

    .toast {
      pointer-events: auto;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 12px 14px;
      background: var(--tbank-surface);
      border: 1px solid var(--tbank-divider);
      border-radius: 14px;
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
      animation: toast-in 0.18s ease-out;
    }

    .toast__dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-top: 7px;
      flex-shrink: 0;
      background: var(--tbank-blue);
    }

    .toast--success .toast__dot {
      background: var(--tbank-green);
    }

    .toast--error .toast__dot {
      background: var(--tbank-red);
    }

    .toast__body {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }

    .toast__title {
      font-weight: 700;
      font-size: 13px;
      color: var(--tbank-text);
    }

    .toast__message {
      font-size: 13px;
      color: var(--tbank-text-muted);
      line-height: 1.35;
    }

    .toast__close {
      background: transparent;
      border: none;
      color: var(--tbank-text-faint);
      cursor: pointer;
      font-size: 13px;
      padding: 2px 4px;
      align-self: flex-start;
    }

    @keyframes toast-in {
      from {
        opacity: 0;
        transform: translateY(-6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  `,
})
export class ToastHost {
  protected readonly notify = inject(NotifyService);
}
