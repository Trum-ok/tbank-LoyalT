import { Component, inject } from '@angular/core';

import { IdentityService, PartnerIdentity } from '../../core/identity.service';

@Component({
  selector: 'app-role-switcher',
  standalone: true,
  templateUrl: './role-switcher.html',
  styleUrl: './role-switcher.scss',
})
export class RoleSwitcher {
  protected readonly identity = inject(IdentityService);

  switchTo(value: string): void {
    const found = this.identity.identities().find(i => this.key(i) === value);
    if (found) {
      this.identity.set(found);
    }
  }

  key(i: PartnerIdentity): string {
    return `${i.account_id ?? ''}__${i.partner_id ?? ''}`;
  }
}
