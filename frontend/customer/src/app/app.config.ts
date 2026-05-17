import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideTaiga } from '@taiga-ui/core';
import { TUI_DEFAULT_LANGUAGE } from '@taiga-ui/i18n';
import { TUI_RUSSIAN_LANGUAGE } from '@taiga-ui/i18n/languages/russian';

import { routes } from './app.routes';
import { customerIdInterceptor } from './core/interceptors/customer-id.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    provideAnimations(),
    provideHttpClient(withInterceptors([customerIdInterceptor])),
    provideTaiga(),
    { provide: TUI_DEFAULT_LANGUAGE, useValue: TUI_RUSSIAN_LANGUAGE },
  ],
};
