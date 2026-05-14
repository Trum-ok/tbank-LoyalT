import { Injectable, computed, inject } from '@angular/core';
import { TUI_DARK_MODE } from '@taiga-ui/core';

export type Theme = 'dark' | 'light';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly dark = inject(TUI_DARK_MODE);

  readonly theme = computed<Theme>(() => (this.dark() ? 'dark' : 'light'));
  readonly isDark = this.dark.asReadonly();

  toggle(): void {
    this.dark.set(!this.dark());
  }

  set(theme: Theme): void {
    this.dark.set(theme === 'dark');
  }
}
