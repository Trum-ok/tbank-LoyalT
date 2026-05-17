import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TuiRoot } from '@taiga-ui/core';
import { catchError, of } from 'rxjs';

import { PartnerApi } from './core/api/partner-api.service';
import { IdentityService } from './core/identity.service';
import { RoleSwitcher } from './shared-ui/role-switcher/role-switcher';
import { ThemeToggle } from './shared-ui/theme-toggle/theme-toggle';
import { ToastHost } from './shared-ui/toast-host/toast-host';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    TuiRoot,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    RoleSwitcher,
    ThemeToggle,
    ToastHost,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly identity = inject(IdentityService);
  private readonly partnerApi = inject(PartnerApi);

  protected readonly partnerName = signal<string | null>(null);
  protected readonly partnerBrand = signal<string | null>(null);
  protected readonly partnerLogo = signal<string | null>(null);

  protected readonly hasPartner = computed(() => this.identity.partnerId() !== null);
  protected readonly partnerInitials = computed(() => {
    const name = this.partnerName() ?? this.identity.current().label;
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(s => s[0]?.toUpperCase() ?? '')
      .join('');
  });

  constructor() {
    this.refreshPartner();
  }

  protected refreshPartner(): void {
    if (!this.identity.accountId()) {
      this.partnerName.set(null);
      this.partnerBrand.set(null);
      this.partnerLogo.set(null);
      return;
    }
    this.partnerApi
      .me()
      .pipe(catchError(() => of(null)))
      .subscribe(p => {
        this.partnerName.set(p?.name ?? null);
        this.partnerBrand.set(p?.brand_color ?? null);
        this.partnerLogo.set(p?.logo_url ?? null);
      });
  }
}
