import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'dashboard',
  },
  {
    path: 'onboarding',
    loadComponent: () =>
      import('./features/onboarding/onboarding-page').then(
        m => m.OnboardingPage,
      ),
    title: 'Подключение к Т-Лояльности',
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard-page').then(m => m.DashboardPage),
    title: 'Дашборд',
  },
  {
    path: 'programs',
    loadComponent: () =>
      import('./features/programs/programs-page').then(m => m.ProgramsPage),
    title: 'Программы лояльности',
  },
  {
    path: 'programs/:id',
    loadComponent: () =>
      import('./features/program-detail/program-detail-page').then(
        m => m.ProgramDetailPage,
      ),
    title: 'Программа',
  },
  {
    path: 'transactions',
    loadComponent: () =>
      import('./features/transactions/transactions-page').then(
        m => m.TransactionsPage,
      ),
    title: 'Транзакции',
  },
  {
    path: 'staff',
    loadComponent: () =>
      import('./features/staff/staff-page').then(m => m.StaffPage),
    title: 'Сотрудники',
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./features/profile/profile-page').then(m => m.ProfilePage),
    title: 'Профиль партнёра',
  },
  { path: '**', redirectTo: 'dashboard' },
];
