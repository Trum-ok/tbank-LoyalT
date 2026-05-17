import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'my-programs',
  },
  {
    path: 'catalog',
    loadComponent: () =>
      import('./features/catalog/catalog-page').then(m => m.CatalogPage),
    title: 'Каталог программ',
  },
  {
    path: 'catalog/:id',
    loadComponent: () =>
      import('./features/program/program-page').then(m => m.ProgramPage),
    title: 'Программа лояльности',
  },
  {
    path: 'my-programs',
    loadComponent: () =>
      import('./features/my-programs/my-programs-page').then(
        m => m.MyProgramsPage,
      ),
    title: 'Мои программы',
  },
  {
    path: 'transactions',
    loadComponent: () =>
      import('./features/transactions/transactions-page').then(
        m => m.TransactionsPage,
      ),
    title: 'История',
  },
  {
    path: 'notifications',
    loadComponent: () =>
      import('./features/notifications/notifications-page').then(
        m => m.NotificationsPage,
      ),
    title: 'Уведомления',
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./features/profile/profile-page').then(m => m.ProfilePage),
    title: 'Мой профиль',
  },
  { path: '**', redirectTo: 'my-programs' },
];
