import { Injectable, signal } from '@angular/core';

export type ToastKind = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  message: string;
}

const DEFAULT_TTL_MS = 3500;

@Injectable({ providedIn: 'root' })
export class NotifyService {
  private nextId = 1;
  readonly toasts = signal<Toast[]>([]);

  success(message: string, title = 'Готово'): void {
    this.push('success', title, message);
  }

  error(message: string, title = 'Ошибка'): void {
    this.push('error', title, message);
  }

  info(message: string, title = 'Подсказка'): void {
    this.push('info', title, message);
  }

  dismiss(id: number): void {
    this.toasts.update(list => list.filter(t => t.id !== id));
  }

  private push(kind: ToastKind, title: string, message: string): void {
    const id = this.nextId++;
    this.toasts.update(list => [...list, { id, kind, title, message }]);
    setTimeout(() => this.dismiss(id), DEFAULT_TTL_MS);
  }
}
