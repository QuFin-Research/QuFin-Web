import { NavGroup } from '@/types';

/**
 * Navigation configuration with RBAC support
 *
 * This configuration is used for both the sidebar navigation and Cmd+K bar.
 * Items are organized into groups, each rendered with a SidebarGroupLabel.
 *
 * RBAC Access Control:
 * Each navigation item can have an `access` property that controls visibility
 * based on permissions, plans, features, roles, and organization context.
 *
 * Examples:
 *
 * 1. Require organization:
 *    access: { requireOrg: true }
 *
 * 2. Require specific permission:
 *    access: { requireOrg: true, permission: 'org:teams:manage' }
 *
 * 3. Require specific plan:
 *    access: { plan: 'pro' }
 *
 * 4. Require specific feature:
 *    access: { feature: 'premium_access' }
 *
 * 5. Require specific role:
 *    access: { role: 'admin' }
 *
 * 6. Multiple conditions (all must be true):
 *    access: { requireOrg: true, permission: 'org:teams:manage', plan: 'pro' }
 *
 * Note: The `visible` function is deprecated but still supported for backward compatibility.
 * Use the `access` property for new items.
 */
export const navGroups: NavGroup[] = [
  {
    label: 'Research',
    items: [
      {
        title: 'Overview',
        url: '/dashboard/overview',
        icon: 'dashboard',
        isActive: false,
        shortcut: ['o', 'o'],
        items: []
      },
      {
        title: 'Markets',
        url: '/dashboard/markets',
        icon: 'markets',
        isActive: false,
        shortcut: ['m', 'm'],
        items: []
      }
    ]
  },
  {
    label: 'Decide',
    items: [
      {
        title: 'Backtest lab',
        url: '/dashboard/backtest',
        icon: 'backtest',
        isActive: false,
        shortcut: ['b', 'b'],
        items: []
      },
      {
        title: 'Decision journal',
        url: '/dashboard/journal',
        icon: 'journal',
        isActive: false,
        shortcut: ['j', 'j'],
        items: []
      }
    ]
  },
  {
    label: 'Account',
    items: [
      {
        title: 'Notifications',
        url: '/dashboard/notifications',
        icon: 'notification',
        isActive: false,
        shortcut: ['n', 'n'],
        items: []
      }
    ]
  }
];
